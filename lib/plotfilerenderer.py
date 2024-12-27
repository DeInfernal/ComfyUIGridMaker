from lib.plotfile import PlotFile, Axis
from PIL import Image, ImageDraw, ImageFont
from comfyui_api import ComfyUIAPI
from lib.filename_sanitizer import sanitize_filename
from lib.htmlrenderer import html_render

import os
import time
import hashlib


class PlotFileRenderer:
    capi = None

    def __init__(self, comfyui_api) -> None:
        if not isinstance(comfyui_api, ComfyUIAPI):
            raise Exception("Cannot initalize PlotFileRenderer - no ComfyUIAPI object provided.")
        self.capi = comfyui_api

    def _prepare_folders(self, plot_object):
        os.makedirs("{}/{}".format("output", plot_object.get_output_folder_name()), exist_ok=True)

    def _flatten_packed_args(self, packed_args: list) -> list:
        # packed_args = [["VAR_SEED", "6"], [["VAR_SPECIES", "VAR_TEST"], ["CAT", "YEPTEST"]], ...]
        answer = []
        for arg in packed_args:
            if isinstance(arg[0], list) or isinstance(arg[0], tuple):
                for subarg in enumerate(arg[0]):
                    answer.append([subarg[1], arg[1][subarg[0]]])
            else:
                answer.append(arg)
        return answer

    def _packed_args_to_sorted_list(self, packed_args: list) -> list:
        # packed_args = [["VAR_SEED", "6"], ["VAR_SPECIES", "CAT"], ...]
        return sorted(self._flatten_packed_args(packed_args))

    def _dictionary_args_to_sorted_list(self, packed_args: dict) -> list:
        return sorted(list(packed_args.items()))

    def _packed_args_to_string(self, packed_args: list) -> list:
        # packed_args = [["VAR_SEED", "6"], ["VAR_SPECIES", "CAT"], ...]
        result = []
        for i in self._packed_args_to_sorted_list(packed_args):
            result.append("{} = {}".format(i[0], i[1]))
        
        # output: VAR_SEED = 6 | VAR_SPECIES = CAT
        return " | ".join(result)

    def _packed_args_to_htmlargs(self, packed_args: list) -> list:
        # packed_args = [["VAR_SEED", "6"], ["VAR_SPECIES", "CAT"], ...]
        result = []
        for i in self._packed_args_to_sorted_list(packed_args):
            result.append("data-{} = \"{}\"".format(i[0].lower(), i[1]))
        
        # output: data-var_seed="6" data-var_species="CAT"
        return " ".join(result)

    def _generate_filename_for_image(self, item, hash: bool = False) -> str:
        # Item is: [["VAR_SEED", "6"], ["VAR_SPECIES", "CAT"], ...]
        # or {'VAR_1': "123"} ...
        # Result doesn't have PNG/JPG extension
        filename = ""

        if isinstance(item, dict):
            xitem = self._dictionary_args_to_sorted_list(item)
        else:
            xitem = self._packed_args_to_sorted_list(item)

        if not hash:
            filename += "img_"
            filename += "_".join(list([i[1] for i in xitem]))
        else:
            stringlist = self._packed_args_to_string(xitem)
            hashedlist = hashlib.sha256(bytes(stringlist, "ansi")).hexdigest()
            filename += hashedlist

        return sanitize_filename(filename)

    def _generate_variables_filenames_pairs(self, plot_object, *axis_objects):
        # Just a preflight checks...
        for axis_object in axis_objects:
            if not isinstance(axis_object, Axis):
                raise Exception("_generate_variables_filenames_pairs received a non-axis object {} - script shutdowned".format(axis_object))

        # Order the axises so when tuples are generated, the first axises should change first, or be overwritten by order
        unordered_axises = list([[axobj.get_order(), axobj] for axobj in axis_objects])

        # Add a number in the position for any unordered stuff
        for obj in enumerate(unordered_axises):
            if obj[1][1].get_order() == 0:
                obj[1][0] += obj[0]

        # Make reversed-ordered list so the bigger numbers go first and the others follow after (meaning bigger numbers change less throughout the generation)
        almost_ordered_axises = sorted(unordered_axises, reverse=True)

        # And make it look like *axis_objects so I don't need to rewrite much
        ordered_axis_objects = list([x[1] for x in almost_ordered_axises])

        # Make a huge list of objects.
        pools = [tuple(axis_object.get_objects()) for axis_object in ordered_axis_objects]

        all_variables_possible_to_generate = [[]]
        for pool in pools:
            all_variables_possible_to_generate = [x+[y] for x in all_variables_possible_to_generate for y in pool]

        # Turn this huge list into a list of [VARIABLES_DICT, FILENAME].
        all_variable_names_possible = [axis_object.get_variable_name() for axis_object in ordered_axis_objects]

        all_items_to_generate = list()
        for item_to_generate in all_variables_possible_to_generate:
            variables = dict()
            for variable_name in enumerate(all_variable_names_possible):
                if isinstance(variable_name[1], list):  # If it is list, then consider going in recursively
                    for subvariable_name in enumerate(variable_name[1]):
                        variables.setdefault(subvariable_name[1], item_to_generate[variable_name[0]][subvariable_name[0]])
                else:  # Else treat it as string
                    variables.setdefault(variable_name[1], item_to_generate[variable_name[0]])
            all_items_to_generate.append((variables, self._generate_filename_for_image(variables, plot_object.get_do_hash_filenames())))
        
        return all_items_to_generate

    def _cleanup_redundant_files(self, directory_to_check, filenames_to_keep):
        filenames = os.listdir("{}/{}".format("output", directory_to_check))
        set_existing = set(filenames)
        set_should_exist = set(filenames_to_keep)
        set_to_delete = set_existing.difference(set_should_exist)
        for item in set_to_delete:
            print("- Deleted redundant file {}".format(item))
            os.remove("{}/{}/{}".format("output", directory_to_check, item))

    def _filter_only_nonexistent_files(self, of_name, unfiltered_items_to_generate):
        filtered_items_to_generate = list()
        for item in unfiltered_items_to_generate:
            imagepath = "{}/{}/{}.png".format("output", of_name, item[1])
            if not os.path.exists(imagepath):
                filtered_items_to_generate.append(item)
        return filtered_items_to_generate

    def _render_all_images(self, plot_object, *axis_objects):
        print("Generation/Rendering: Started at {}...".format(time.ctime()))

        # Some variables for convinience
        of_name = plot_object.get_output_folder_name()

        # Make filename-other pairs, filtered by existence (so only seek files that doesn't exist)
        all_items_to_generate = self._generate_variables_filenames_pairs(plot_object, *axis_objects)
        print("The XY plot consists of {} images.".format(len(all_items_to_generate)))

        # If there is cleanup then clean up.
        if plot_object.get_cleanup():
            filenames_to_cleanup = ["{}.png".format(x[1]) for x in all_items_to_generate]
            self._cleanup_redundant_files(of_name, filenames_to_cleanup)

        all_items_to_generate = self._filter_only_nonexistent_files(of_name, all_items_to_generate)

        # Finally, generate all images.
        # ...also track time, just for convinience.
        current_timestamp = time.time()
        current_progress = 0
        maximum_progress = len(all_items_to_generate)

        print("Preparing to generate {} images that wasn't found on the PC...".format(maximum_progress))

        for item_to_generate in all_items_to_generate:
            imagepath = "output/{}/{}.png".format(of_name, item_to_generate[1])
            if os.path.exists(imagepath):
                print("! {}".format(item_to_generate[1]))  # Technically speaking, this is quite worthless as I already filter nonexistants, but... well, let it be here for purposes.
            else:
                rendered_workflow = plot_object.generate_workflow(item_to_generate[0])
                self.capi.generate_image(rendered_workflow, imagepath)
                print("+ {}".format(item_to_generate[1]))

            # And all of this is to track the progress of time. For convinience, of course.
            current_progress += 1
            progress_percentage = current_progress/maximum_progress*10000//1/100
            new_timestamp = time.time()
            elapsed_time = (new_timestamp - current_timestamp) * 100 // 1 / 100
            seconds_left_till_finish = (maximum_progress - current_progress) * elapsed_time
            sensible_time_timestamp = time.ctime(new_timestamp + seconds_left_till_finish)
            print("Progress: {} of {} ({}%), ETA of completion: {}.".format(current_progress, maximum_progress, progress_percentage, sensible_time_timestamp))
            current_timestamp = new_timestamp

        print("Generation/Rendering: Finished at {}...".format(time.ctime()))

    def _make_label(self, image_object: Image, bbox: tuple, var_name, var_value, margin: int = 20):
        # Try to generate text that is as big as possible, within margins.
        x_size = bbox[2] - bbox[0] - margin
        y_size = bbox[3] - bbox[1] - margin
        x_size_b = x_size + margin
        y_size_b = y_size + margin

        draw = ImageDraw.Draw(image_object)
        pos_x = (bbox[2] + bbox[0])/2//1
        pos_y = (bbox[3] + bbox[1])/2//1

        text = "{}\n=\n{}".format(var_name, var_value)
        fontsize = 1024

        while x_size_b > x_size or y_size_b > y_size:
            if x_size_b / x_size > 4.0 and y_size_b / y_size > 4.0:
                fontsize = int(fontsize / 2)
            else:
                fontsize -= 4

            font = ImageFont.FreeTypeFont("font.ttf", fontsize)
            if fontsize <= 5:
                break

            t_bbox = draw.multiline_textbbox((pos_x, pos_y), text, font, "mm", 4, "center")
            x_size_b = t_bbox[2] - t_bbox[0]
            y_size_b = t_bbox[3] - t_bbox[1]
            # print("DEBUG: {} = Possible {}x{} {}, getbbox {}x{} {}".format(fontsize, x_size, y_size, bbox, x_size_b, y_size_b, t_bbox))

        draw.multiline_text((pos_x, pos_y), text, (0,0,0), font, "mm", 4, "center")

    def _paste_image(self, image_object: Image, image_path: str, x_offset: int, y_offset: int, resize_ratio: float = None):
        rendered_image = Image.open(image_path)
        if resize_ratio:
            rendered_image = rendered_image.resize((int(rendered_image.width * resize_ratio), int(rendered_image.height * resize_ratio)))
        image_object.paste(rendered_image, (x_offset, y_offset))

    def make_infinite_plot(self, plot_object: PlotFile, extra_objects: list = None, plot_size = None):
        # Extra Objects should contain ONLY objects down from Axis 3.
        # If plot_size is not specified, then do whatever.
        if plot_size is None:
            plot_size = plot_object.get_axis_amount()
        if extra_objects is None:
            extra_objects = list()

        # Now let's generate our infinite combo wombo
        if plot_size == 1:
            #  ___ _    ___ _____   ___ ___ _______         _     ___ ___ __  __ ___ _  _ ___ ___ ___  _  _
            # | _ \ |  / _ \_   _| / __|_ _|_  / __|  ___  / |___|   \_ _|  \/  | __| \| / __|_ _/ _ \| \| |
            # |  _/ |_| (_) || |   \__ \| | / /| _|  |___| | |___| |) | || |\/| | _|| .` \__ \| | (_) | .` |
            # |_| |____\___/ |_|   |___/___/___|___|       |_|   |___/___|_|  |_|___|_|\_|___/___\___/|_|\_|

            # So, it is plot size = 1, so it is a one-liner. A unique render, must be handled separately altogether.
            print("Generation of 1-axis (X-only) structure: Started at {}...".format(time.ctime()))

            x_axisobject = plot_object.get_axis_object(0)  # ID: 0, X-Axis.
            x_axis_variable_name = x_axisobject.get_variable_name()

            single_image_width = plot_object.get_image_width()
            single_image_height = plot_object.get_image_height()

            y_text_offset = 200

            if plot_object.get_resize_ratio() is not None:
                single_image_width = int(single_image_width * plot_object.get_resize_ratio())
                single_image_height = int(single_image_height * plot_object.get_resize_ratio())
                y_text_offset = int(200 * plot_object.get_resize_ratio())

            total_width = single_image_width * x_axisobject.get_object_count()
            total_height = single_image_height + y_text_offset

            of_name = plot_object.get_output_folder_name()

            # Make empty image
            imageObject = Image.new("RGB", (total_width, total_height), (255, 128, 0))

            for x_axis in enumerate(x_axisobject.get_objects()):
                # Make object name easier to access
                variables_stack = [[x_axis_variable_name, x_axis[1]]]
                renderedImageName = "output/{}/{}.png".format(of_name, self._generate_filename_for_image(variables_stack, plot_object.get_do_hash_filenames()))

                # Paste image with specific offsets
                self._paste_image(imageObject, renderedImageName, x_axis[0]*single_image_width, y_text_offset, plot_object.get_resize_ratio())

                # Generate label for image.
                pos_bbox = (x_axis[0]*single_image_width, 0, x_axis[0]*single_image_width + single_image_width, y_text_offset)
                self._make_label(imageObject, pos_bbox, x_axis_variable_name, x_axis[1])

            print("Generation of 1-axis (X-only) structure: Ended at {}...".format(time.ctime()))
            return imageObject
        elif plot_size == 2:  # Plot = 2, so a final XY render.
            #  ___ _    ___ _____   ___ ___ _______         ___    ___ ___ __  __ ___ _  _ ___ ___ ___  _  _
            # | _ \ |  / _ \_   _| / __|_ _|_  / __|  ___  |_  )__|   \_ _|  \/  | __| \| / __|_ _/ _ \| \| |
            # |  _/ |_| (_) || |   \__ \| | / /| _|  |___|  / /___| |) | || |\/| | _|| .` \__ \| | (_) | .` |
            # |_| |____\___/ |_|   |___/___/___|___|       /___|  |___/___|_|  |_|___|_|\_|___/___\___/|_|\_|

            # So, a plot size = 2, a main building block of any higher-dimension items.
            # Must remember: extra_objects is a list of [["VAR_SEED", 12], ["VAR_BLA", "BLA"]]
            print("Generation of 2-axis (XY-plot) structure: Started at {}...".format(time.ctime()))

            x_axisobject = plot_object.get_axis_object(0)  # ID: 0, X-Axis.
            x_axis_variable_name = x_axisobject.get_variable_name()
            y_axisobject = plot_object.get_axis_object(1)  # ID: 1, Y-Axis.
            y_axis_variable_name = y_axisobject.get_variable_name()

            single_image_width = plot_object.get_image_width()
            single_image_height = plot_object.get_image_height()

            amount_of_x_objects_to_generate = x_axisobject.get_object_count()
            amount_of_y_objects_to_generate = y_axisobject.get_object_count()

            x_text_offset = 400
            y_text_offset = 200

            if plot_object.get_resize_ratio() is not None:
                single_image_width = int(single_image_width * plot_object.get_resize_ratio())
                single_image_height = int(single_image_height * plot_object.get_resize_ratio())
                x_text_offset = int(400 * plot_object.get_resize_ratio())
                y_text_offset = int(200 * plot_object.get_resize_ratio())

            total_width = single_image_width * amount_of_x_objects_to_generate + x_text_offset
            total_height = single_image_height * amount_of_y_objects_to_generate + y_text_offset

            of_name = plot_object.get_output_folder_name()

            imageObject = Image.new("RGB", (total_width, total_height), (255, 128, 0))

            for x_axis in enumerate(x_axisobject.get_objects()):
                for y_axis in enumerate(y_axisobject.get_objects()):
                    # Make object name easier to access and to generate normal filename
                    variables_stack = [[x_axis_variable_name, x_axis[1]], [y_axis_variable_name, y_axis[1]]] + list(extra_objects)
                    renderedImageName = "output/{}/{}.png".format(of_name, self._generate_filename_for_image(variables_stack, plot_object.get_do_hash_filenames()))

                    # Paste image with specific offsets
                    self._paste_image(imageObject, renderedImageName, x_axis[0]*single_image_width+x_text_offset, y_axis[0]*single_image_height+y_text_offset, plot_object.get_resize_ratio())

            for x_axis in enumerate(x_axisobject.get_objects()):
                # Generate labels for images.
                pos_bbox = (x_text_offset + x_axis[0]*single_image_width, 0, x_text_offset + x_axis[0]*single_image_width + single_image_width, y_text_offset)
                self._make_label(imageObject, pos_bbox, x_axis_variable_name, x_axis[1])

            for y_axis in enumerate(y_axisobject.get_objects()):
                # Generate labels for images.
                pos_bbox = (0, y_text_offset + y_axis[0] * single_image_height, x_text_offset, y_text_offset + y_axis[0] * single_image_height + single_image_height)
                self._make_label(imageObject, pos_bbox, y_axis_variable_name, y_axis[1])

            print("Generation of 2-axis (XY-plot) structure: Ended at {}...".format(time.ctime()))
            return imageObject
        elif plot_size % 2 == 1:
            #  ___ _    ___ _____   ___ ___ _______         ___ _  _ ___ ___ _  _ ___ _____ ___    ___  ___  ___
            # | _ \ |  / _ \_   _| / __|_ _|_  / __|  ___  |_ _| \| | __|_ _| \| |_ _|_   _| __|  / _ \|   \|   \
            # |  _/ |_| (_) || |   \__ \| | / /| _|  |___|  | || .` | _| | || .` || |  | | | _|  | (_) | |) | |) |
            # |_| |____\___/ |_|   |___/___/___|___|       |___|_|\_|_| |___|_|\_|___| |_| |___|  \___/|___/|___/

            # Plot size is ODD (3, 5, 7). Then it is considered a one-liner of previous iteration.
            print("Generation of {}-axis structure: Started at {}...".format(plot_size, time.ctime()))

            x_axisobject = plot_object.get_axis_object(plot_size-1)  # ID: Last one, so before it comes XY plot, or XYZW plot, etc...
            x_axis_variable_name = x_axisobject.get_variable_name()

            amount_of_x_objects_to_generate = x_axisobject.get_object_count()

            x_text_offset = 800 * (2 ** ( (plot_size - 3) // 2 ) )
            y_text_offset = 400 * (2 ** ( (plot_size - 3) // 2 ) )

            if plot_object.get_resize_ratio() is not None:
                x_text_offset = int(800 * (2 ** ( (plot_size - 3) // 2 ) ) * plot_object.get_resize_ratio())
                y_text_offset = int(400 * (2 ** ( (plot_size - 3) // 2 ) ) * plot_object.get_resize_ratio())

            past_plot_images = []
            for x_axis in enumerate(x_axisobject.get_objects()):
                past_plot_images.append(self.make_infinite_plot(plot_object, [[x_axis_variable_name, x_axis[1]]] + extra_objects, plot_size - 1))

            single_pastplot_width = past_plot_images[0].width
            single_pastplot_height = past_plot_images[0].height
            colorOffset = min(128, 16 * (2 ** ( (plot_size - 3) // 2 ) ))

            if plot_object.get_autoflip_last_axis():
                total_width_unflipped = single_pastplot_width * amount_of_x_objects_to_generate
                total_height_unflipped = single_pastplot_height + y_text_offset
                total_width_flipped = single_pastplot_width + x_text_offset
                total_height_flipped = single_pastplot_height * amount_of_x_objects_to_generate

                ratio_unflipped = max(total_width_unflipped, total_height_unflipped) / min(total_width_unflipped, total_height_unflipped)
                ratio_flipped = max(total_width_flipped, total_height_flipped) / min(total_width_flipped, total_height_flipped)
                # Logic: The closer ratio to 1, the closer image to a square. Choose the closest one.
                plot_object.set_flip_last_axis(ratio_flipped < ratio_unflipped)
                if plot_object.get_flip_last_axis():
                    print("Autoflip has kicked in and decided that your last axis is better to be made in vertically.")

            if plot_object.get_flip_last_axis():
                total_width = single_pastplot_width + x_text_offset
                total_height = single_pastplot_height * amount_of_x_objects_to_generate

                imageObject = Image.new("RGB", (total_width, total_height), (255, 128+colorOffset, 0+colorOffset*2))

                for x_axis in enumerate(x_axisobject.get_objects()):
                    # Paste image with specific offsets
                    x_offset = x_text_offset
                    y_offset = x_axis[0] * single_pastplot_height
                    imageObject.paste(past_plot_images[x_axis[0]], (x_offset, y_offset))

                for x_axis in enumerate(x_axisobject.get_objects()):
                    # Generate labels for images.
                    pos_bbox = (0, x_axis[0]*single_pastplot_height, x_text_offset, x_axis[0]*single_pastplot_height+single_pastplot_height)
                    self._make_label(imageObject, pos_bbox, x_axis_variable_name, x_axis[1])
            else:
                total_width = single_pastplot_width * amount_of_x_objects_to_generate
                total_height = single_pastplot_height + y_text_offset

                imageObject = Image.new("RGB", (total_width, total_height), (255, 128+colorOffset, 0+colorOffset*2))

                for x_axis in enumerate(x_axisobject.get_objects()):
                    # Paste image with specific offsets
                    x_offset = x_axis[0] * single_pastplot_width
                    y_offset = y_text_offset
                    imageObject.paste(past_plot_images[x_axis[0]], (x_offset, y_offset))

                for x_axis in enumerate(x_axisobject.get_objects()):
                    # Generate labels for images.
                    pos_bbox = (x_axis[0]*single_pastplot_width, 0, x_axis[0]*single_pastplot_width + single_pastplot_width, y_text_offset)
                    self._make_label(imageObject, pos_bbox, x_axis_variable_name, x_axis[1])

            print("Generation of {}-axis structure: Ended at {}...".format(plot_size, time.ctime()))
            return imageObject
        elif plot_size % 2 == 0:
            #  ___ _    ___ _____   ___ ___ _______         ___ _  _ ___ ___ _  _ ___ _____ ___   _____   _____ _  _
            # | _ \ |  / _ \_   _| / __|_ _|_  / __|  ___  |_ _| \| | __|_ _| \| |_ _|_   _| __| | __\ \ / / __| \| |
            # |  _/ |_| (_) || |   \__ \| | / /| _|  |___|  | || .` | _| | || .` || |  | | | _|  | _| \ V /| _|| .` |
            # |_| |____\___/ |_|   |___/___/___|___|       |___|_|\_|_| |___|_|\_|___| |_| |___| |___| \_/ |___|_|\_|

            # Plot size is EVEN (4, 6, 8). Then it is considered a XY-plot of previous iteration.
            print("Generation of {}-axis structure: Started at {}...".format(plot_size, time.ctime()))

            x_axisobject = plot_object.get_axis_object(plot_size-2)  # ID: Almost Last one, so before it comes XY plot, or XYZW plot, etc...
            x_axis_variable_name = x_axisobject.get_variable_name()
            y_axisobject = plot_object.get_axis_object(plot_size-1)  # ID: Last one, so before it comes XY plot, or XYZW plot, etc...
            y_axis_variable_name = y_axisobject.get_variable_name()

            amount_of_x_objects_to_generate = x_axisobject.get_object_count()
            amount_of_y_objects_to_generate = y_axisobject.get_object_count()

            x_text_offset = 800 * (2 ** ( (plot_size - 3) // 2 ) )
            y_text_offset = 400 * (2 ** ( (plot_size - 3) // 2 ) )

            if plot_object.get_resize_ratio() is not None:
                x_text_offset = int(800 * (2 ** ( (plot_size - 3) // 2 ) ) * plot_object.get_resize_ratio())
                y_text_offset = int(400 * (2 ** ( (plot_size - 3) // 2 ) ) * plot_object.get_resize_ratio())

            past_plot_images = dict()
            for x_axis in enumerate(x_axisobject.get_objects()):
                for y_axis in enumerate(y_axisobject.get_objects()):
                    past_plot_images.setdefault((x_axis[0], y_axis[0]), self.make_infinite_plot(plot_object, [[x_axis_variable_name, x_axis[1]], [y_axis_variable_name, y_axis[1]]] + extra_objects, plot_size - 2))

            single_pastplot_width = past_plot_images.get((0, 0)).width
            single_pastplot_height = past_plot_images.get((0, 0)).height

            total_width = single_pastplot_width * amount_of_x_objects_to_generate + x_text_offset
            total_height = single_pastplot_height * amount_of_y_objects_to_generate + y_text_offset

            colorOffset = min(128, 16 * (2 ** ( (plot_size - 3) // 2 ) ))
            imageObject = Image.new("RGB", (total_width, total_height), (255, 128+colorOffset, 0+colorOffset*2))

            for x_axis in enumerate(x_axisobject.get_objects()):
                for y_axis in enumerate(y_axisobject.get_objects()):
                    # Paste image with specific offsets
                    x_offset = x_axis[0] * single_pastplot_width + x_text_offset
                    y_offset = y_axis[0] * single_pastplot_height + y_text_offset
                    imageObject.paste(past_plot_images.get((x_axis[0], y_axis[0])), (x_offset, y_offset))

            for x_axis in enumerate(x_axisobject.get_objects()):
                # Generate labels for images.
                pos_bbox = (x_axis[0]*single_pastplot_width + x_text_offset, 0, x_axis[0]*single_pastplot_width + single_pastplot_width + x_text_offset, y_text_offset)
                self._make_label(imageObject, pos_bbox, x_axis_variable_name, x_axis[1])

            for y_axis in enumerate(y_axisobject.get_objects()):
                # Generate labels for images.
                pos_bbox = (0, y_axis[0] * single_pastplot_height + y_text_offset, x_text_offset, y_axis[0] * single_pastplot_height + single_pastplot_height + y_text_offset)
                self._make_label(imageObject, pos_bbox, y_axis_variable_name, y_axis[1])

            print("Generation of {}-axis structure: Ended at {}...".format(plot_size, time.ctime()))
            return imageObject

    def make_infinite_plot_htmltable(self, plot_object: PlotFile, extra_objects: list = None, plot_size = None):
        # Extra Objects should contain ONLY objects down from Axis 3.
        # If plot_size is not specified, then do whatever.
        if plot_size is None:
            plot_size = plot_object.get_axis_amount()
        if extra_objects is None:
            extra_objects = list()

        # Now let's generate our infinite combo wombo
        if plot_size == 1:  # Plot = 1, so one-liner. A unique render.
            # print("Generation of 1-axis (X-only) HTML-structure: Started at {}...".format(time.ctime()))

            x_axisobject = plot_object.get_axis_object(0)  # ID: 0, X-Axis.
            x_axis_variable_name = x_axisobject.get_variable_name()

            of_name = plot_object.get_output_folder_name()

           # Pregenerate previous tables
            past_plot_image_names = []
            for x_axis in enumerate(x_axisobject.get_objects()):
                # Make object name easier to access
                renderedImageName = "{}/{}.png".format(of_name, self._generate_filename_for_image([[x_axis_variable_name, x_axis[1]]], plot_object.get_do_hash_filenames()))
                past_plot_image_names.append(renderedImageName)

            # Begin assembling final table
            table = '<table class="plot_depth_1">'

            row_names = ""
            row_tables = ""

            for x_axis in enumerate(x_axisobject.get_objects()):
                # Paste rows
                row_names += "<td>{} = {}</td>".format(x_axis_variable_name, x_axis[1])  # Add to name row
                ppin = past_plot_image_names[x_axis[0]]
                row_tables += '<td><img class="plot_img" src="{}"></td>'.format(ppin)  # Add to table row a previously rendered table
            table += '<tr class="plot_depth_1">{}</tr><tr class="plot_depth_1">{}</tr>'.format(row_names, row_tables)

            table += "</table>"

            # print("Generation of 1-axis (X-only) HTML-structure: Ended at {}...".format(time.ctime()))
            return table
        elif plot_size == 2:  # Plot = 2, so a final XY render.
            # print("Generation of 2-axis (XY-plot) HTML-structure: Started at {}...".format(time.ctime()))

            x_axisobject = plot_object.get_axis_object(0)  # ID: 0, X-Axis.
            x_axis_variable_name = x_axisobject.get_variable_name()
            y_axisobject = plot_object.get_axis_object(1)  # ID: 1, Y-Axis.
            y_axis_variable_name = y_axisobject.get_variable_name()

            of_name = plot_object.get_output_folder_name()

            past_plot_image_names = dict()
            for x_axis in enumerate(x_axisobject.get_objects()):
                for y_axis in enumerate(y_axisobject.get_objects()):
                    # Make object name easier to access and to generate normal filename
                    all_arguments = [[x_axis_variable_name, x_axis[1]], [y_axis_variable_name, y_axis[1]]] + list(extra_objects)
                    renderedImageName = "{}/{}.png".format(of_name, self._generate_filename_for_image(all_arguments, plot_object.get_do_hash_filenames()))

                    past_plot_image_names.setdefault((x_axis[0], y_axis[0]), renderedImageName)

            # Begin assembling final table
            table = '<table class="plot_depth_2">'

            # First, assemble the header row
            table += '<tr class="plot_depth_2">'
            table += "<td></td>"  # The first element is belonging to Y column, therefore empty.
            for x_axis in enumerate(x_axisobject.get_objects()):
                table += "<td>{} = {}</td>".format(x_axis_variable_name, x_axis[1])
            table += "</tr>"

            # Then assemble image rows
            for y_axis in enumerate(y_axisobject.get_objects()):
                table += '<tr class="plot_depth_2"><td>{} = {}</td>'.format(y_axis_variable_name, y_axis[1])
                for x_axis in enumerate(x_axisobject.get_objects()):
                    ppin = past_plot_image_names.get((x_axis[0], y_axis[0]))
                    all_arguments = [[x_axis_variable_name, x_axis[1]], [y_axis_variable_name, y_axis[1]]] + list(extra_objects)
                    rendered_arguments = self._packed_args_to_string(all_arguments)
                    html_arguments = self._packed_args_to_htmlargs(all_arguments)
                    table += '<td><img class="plot_img" src="{}" data-caption="{}" {}></td>'.format(ppin, rendered_arguments, html_arguments)
                table += "</tr>"

            # Finally, close the table.
            table += "</table>"

            # print("Generation of 2-axis (XY-plot) HTML-structure: Ended at {}...".format(time.ctime()))
            return table
        elif plot_size % 2 == 1:  # Plot size is ODD (3, 5, 7). Then it is considered a one-liner of previous iteration.
            # print("Generation of {}-axis HTML-structure: Started at {}...".format(plot_size, time.ctime()))

            x_axisobject = plot_object.get_axis_object(plot_size-1)  # ID: Last one, so before it comes XY plot, or XYZW plot, etc...
            x_axis_variable_name = x_axisobject.get_variable_name()

            # Pregenerate previous tables
            past_plot_tables = []
            for x_axis in enumerate(x_axisobject.get_objects()):
                past_plot_tables.append(self.make_infinite_plot_htmltable(plot_object, [[x_axis_variable_name, x_axis[1]]] + extra_objects, plot_size - 1))

            # Begin assembling final table
            table = '<table class="plot_depth_{}">'.format(plot_size)

            row_names = ""
            row_tables = ""

            for x_axis in enumerate(x_axisobject.get_objects()):
                # Paste rows
                row_names += "<td>{} = {}</td>".format(x_axis_variable_name, x_axis[1])  # Add to name row
                row_tables += "<td>{}</td>".format(past_plot_tables[x_axis[0]])  # Add to table row a previously rendered table
            table += '<tr class="plot_depth_{}">{}</tr><tr class="plot_depth_{}">{}</tr>'.format(plot_size, row_names, plot_size, row_tables)

            table += "</table>"

            # print("Generation of {}-axis HTML-structure: Ended at {}...".format(plot_size, time.ctime()))
            return table
        elif plot_size % 2 == 0:  # Plot size is EVEN (4, 6, 8). Then it is considered a XY-plot of previous iteration.
            # print("Generation of {}-axis HTML-structure: Started at {}...".format(plot_size, time.ctime()))

            x_axisobject = plot_object.get_axis_object(plot_size-2)  # ID: Almost Last one, so before it comes XY plot, or XYZW plot, etc...
            x_axis_variable_name = x_axisobject.get_variable_name()
            y_axisobject = plot_object.get_axis_object(plot_size-1)  # ID: Last one, so before it comes XY plot, or XYZW plot, etc...
            y_axis_variable_name = y_axisobject.get_variable_name()

            past_plot_tables = dict()
            for x_axis in enumerate(x_axisobject.get_objects()):
                for y_axis in enumerate(y_axisobject.get_objects()):
                    past_plot_tables.setdefault((x_axis[0], y_axis[0]), self.make_infinite_plot_htmltable(plot_object, [[x_axis_variable_name, x_axis[1]], [y_axis_variable_name, y_axis[1]]] + extra_objects, plot_size - 2))

            # Begin assembling final table
            table = '<table class="plot_depth_{}">'.format(plot_size)

            # First, assemble the header row
            table += '<tr class="plot_depth_{}">'.format(plot_size)
            table += "<td></td>"  # The first element is belonging to Y column, therefore empty.
            for x_axis in enumerate(x_axisobject.get_objects()):
                table += "<td>{} = {}</td>".format(x_axis_variable_name, x_axis[1])
            table += "</tr>"

            # Then assemble image rows
            for y_axis in enumerate(y_axisobject.get_objects()):
                table += '<tr class="plot_depth_{}"><td>{} = {}</td>'.format(plot_size, y_axis_variable_name, y_axis[1])
                for x_axis in enumerate(x_axisobject.get_objects()):
                    table += "<td>{}</td>".format(past_plot_tables.get((x_axis[0], y_axis[0])))
                table += "</tr>"

            # Finally, close the table.
            table += "</table>"

            # print("Generation of {}-axis HTML-structure: Ended at {}...".format(plot_size, time.ctime()))
            return table

    def render(self, plot_object, **kwargs):
        self._prepare_folders(plot_object)

        plot_object.set_do_hash_filenames(kwargs.get("hash_filenames"))
        plot_object.set_cleanup(kwargs.get("cleanup"))

        if kwargs.get("make_html_table"):  # We will make the file beforehand so it can be filled dynamically! >:D
            with open("output/{}{}.html".format(plot_object.get_output_folder_name(), plot_object.get_output_file_suffix()), "w", encoding="utf-8") as fstream:
                fstream.write(html_render(plot_object, self.make_infinite_plot_htmltable(plot_object)))

        self._render_all_images(plot_object, *plot_object.axises)

        if not kwargs.get("skip_mass_generation"):
            if "resize_ratio" in kwargs:
                plot_object.set_resize_ratio(kwargs.get("resize_ratio", 1.0))

            plot_object.set_ignore_non_replacements(kwargs.get("ignore_non_replacements"))
            plot_object.set_flip_last_axis(kwargs.get("flip_last_axis"))
            plot_object.set_autoflip_last_axis(kwargs.get("autoflip_last_axis"))

            image = self.make_infinite_plot(plot_object)

            if "autoreduce" in kwargs:
                if image.width > kwargs.get("autoreduce") or image.height > kwargs.get("autoreduce"):
                    maxsize = max(image.width, image.height)
                    print("Autoreduce kicked in since one of the dimensions of image is {} out of {}...".format(maxsize, kwargs.get("autoreduce")))
                    newratio = kwargs.get("autoreduce") / maxsize
                    image = image.resize((int(image.width*newratio), int(image.height*newratio)))

            image.save("output/{}{}.png".format(plot_object.get_output_folder_name(), plot_object.get_output_file_suffix()))

        if not kwargs.get("yes"):
            input("Render completed. Press ENTER to exit the script.")
