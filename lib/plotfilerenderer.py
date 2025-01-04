from lib.plotfile import PlotFile, Axis
from PIL import Image, ImageDraw, ImageFont
from comfyui_api import ComfyUIAPI
from lib.filename_sanitizer import sanitize_filename
from lib.htmlrenderer import InfiniteRenderer, SmallPlotRenderer

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
            hashedlist = hashlib.sha256(bytes(stringlist, "U8")).hexdigest()
            filename += hashedlist

        return sanitize_filename(filename)

    def _generate_variables_filenames_pairs(self, plot_object, *axis_objects):
        # Outputs ordered list of object like
        # [
        #    { DICT of all variables, expanded;  Hashed name without .png;  DICT of AXIS_ID: AXIS_ITEM_ID }, -- the last part is for HTML pages, actually.
        #    { {VAR_A: 1, VAR_B: 2}, "hashedname1", {0: 1, 1: 0} },
        #    { {VAR_A: 1, VAR_B: 3}, "hashedname2", {0: 1, 1: 1} }...
        # ]

        # STEP 0: Preflight check - we need actual AXIS OBJECT.
        for axis_object in axis_objects:
            if not isinstance(axis_object, Axis):
                raise Exception("_generate_variables_filenames_pairs received a non-axis object {} - script shutdowned".format(axis_object))

        # STEP 1: Create the list with perfect order (goal is to have ordered AXIS lists)
        # GOAL OF THE STEP: To achieve a list of dictionaries in form of AXIS_ID: AXIS_VALUE_ID, so it could later be either unpacked to a better item sorting function.

        # 1. Get all ORDER numbers, and if there isn't one, the ID of the axis. The bigger number should mean "Get me changed last" when rendering.
        list_of_unordered_axisobjects_and_their_orders = list([[axobj.get_order() if axobj.get_order() > 0 else axobj.get_id(), axobj] for axobj in axis_objects])

        # 2. Reverse the list, so the bigger numbers go first and the others follow after (meaning bigger numbers change less throughout the generation)
        sorted_list_of_axisobjects_and_their_orders = sorted(list_of_unordered_axisobjects_and_their_orders, reverse=True)

        # 3. Now, with ordered items axises, we can ditch the ordering and leave only Axis Objects.
        list_of_ordered_axisobjects = list([x[1] for x in sorted_list_of_axisobjects_and_their_orders])

        # 4. Create same amount of pools as there is axises, with all item ids within them
        ordered_pools = [tuple(axis_object.get_objects_as_ids()) for axis_object in list_of_ordered_axisobjects]

        # 5. Generate the all variants possible in the order of sorted.
        # So lets imagine that pools is [a,b,c] + [1,2,3] + [i,ii,iii]
        # Initially there will be only empty list in the pool ( [] )
        # Then for each pool that is already sorted by the weight (meaning order: 999 comes first, and changes last)
        # Regenerate all_variables_possible_to_generate with a dict of current pool. Meaning there is next iterations:
        # [] + [a]; [] + [b]; [] + [c] -> [[a], [b], [c]]
        # [a] + [1]; [a] + [2]; [a] + [3]; [b] + [1] ... -> [[a, 1], [a, 2], [a, 3], [b, 1], [b, 2], [b, 3]] (see how A changes to B only after all 123 gone?)
        # [a, 1] + [i], [a, 1] + [ii], ... [c, 3] + [i], [c, 3] + [ii].. -> [[a, 1, i], [a, 1, ii], [a, 1, iii], [a, 2, i], [a, 2, ii]... ] (again, only after all iii changed, the number 123 changes)
        list_of_lists_of_axisobjects_values_to_be_generated = [[]]
        for pool in ordered_pools:
            list_of_lists_of_axisobjects_values_to_be_generated = [x+[y] for x in list_of_lists_of_axisobjects_values_to_be_generated for y in pool]

        # 6. Now let's zip the AXIS ID to their corresponding variables.
        zipped_things_to_generate = []
        for single_variable_list in list_of_lists_of_axisobjects_values_to_be_generated:
            dict_of_things_to_zip = dict()
            for enum_variable_id, enum_variable_value in enumerate(single_variable_list):
                dict_of_things_to_zip.setdefault(list_of_ordered_axisobjects[enum_variable_id].get_id(), enum_variable_value)
            zipped_things_to_generate.append(dict_of_things_to_zip)

        # At this point we got a list looking like that:
        # [ {3: 1, 2: 4, 0: 2}, ... ] winch correspond to a axis ID and the item of this id. Perfect.

        # STEP 2: Now we need to make a full variable list like {VAR_A:17, VAR_B:solo} and generate a hashed name for those.
        resulting_list_of_items_to_generate = list()

        for item_to_generate in zipped_things_to_generate:  # item_to_generate = {3: 1, 5: 12, 0: 2 --> (AXIS_ID: AXIS_VALUE_ID)}
            unpacked_variables = dict()
            for axis_id, axis_value_id in item_to_generate.items():
                # Get the variable name/s
                axis_object = plot_object.get_axis_object(axis_id)
                axis_variable_name = axis_object.get_variable_name()
                axis_variable_value = axis_object.get_object_id(axis_value_id)

                # If variable name is a string, then just add it as-is.
                if isinstance(axis_variable_name, str):
                    unpacked_variables.setdefault(axis_variable_name, axis_variable_value)

                # If not a string, then it could only be List Of Strings. Then we need to unpack them, too.
                else:
                    for sub_axis_id in range(len(axis_variable_name)):
                        unpacked_variables.setdefault(axis_variable_name[sub_axis_id], axis_variable_value[sub_axis_id])

            # At this point, unpacked_variables look like {VAR_A: test, VAR_B: 42}. This is enough to make a hashed filename.
            item_basic_filename = self._generate_filename_for_image(unpacked_variables, plot_object.get_do_hash_filenames())

            # Finally, assemble the item.
            finished_item = [
                unpacked_variables,
                item_basic_filename,
                item_to_generate
            ]

            # And append it to output result
            resulting_list_of_items_to_generate.append(finished_item)

        return resulting_list_of_items_to_generate

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

        draw.multiline_text((pos_x, pos_y), text, (0, 0, 0), font, "mm", 4, "center")

    def _paste_image(self, image_object: Image, image_path: str, x_offset: int, y_offset: int, resize_ratio: float = None):
        rendered_image = Image.open(image_path)
        if resize_ratio:
            rendered_image = rendered_image.resize((int(rendered_image.width * resize_ratio), int(rendered_image.height * resize_ratio)))
        image_object.paste(rendered_image, (x_offset, y_offset))

    def make_infinite_plot(self, plot_object: PlotFile, extra_objects: list = None, plot_size=None):
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

            x_text_offset = 800 * (2 ** ((plot_size - 3) // 2))
            y_text_offset = 400 * (2 ** ((plot_size - 3) // 2))

            if plot_object.get_resize_ratio() is not None:
                x_text_offset = int(800 * (2 ** ((plot_size - 3) // 2)) * plot_object.get_resize_ratio())
                y_text_offset = int(400 * (2 ** ((plot_size - 3) // 2)) * plot_object.get_resize_ratio())

            past_plot_images = []
            for x_axis in enumerate(x_axisobject.get_objects()):
                past_plot_images.append(self.make_infinite_plot(plot_object, [[x_axis_variable_name, x_axis[1]]] + extra_objects, plot_size - 1))

            single_pastplot_width = past_plot_images[0].width
            single_pastplot_height = past_plot_images[0].height
            colorOffset = min(128, 16 * (2 ** ((plot_size - 3) // 2)))

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

            x_text_offset = 800 * (2 ** ((plot_size - 3) // 2))
            y_text_offset = 400 * (2 ** ((plot_size - 3) // 2))

            if plot_object.get_resize_ratio() is not None:
                x_text_offset = int(800 * (2 ** ((plot_size - 3) // 2)) * plot_object.get_resize_ratio())
                y_text_offset = int(400 * (2 ** ((plot_size - 3) // 2)) * plot_object.get_resize_ratio())

            past_plot_images = dict()
            for x_axis in enumerate(x_axisobject.get_objects()):
                for y_axis in enumerate(y_axisobject.get_objects()):
                    past_plot_images.setdefault((x_axis[0], y_axis[0]), self.make_infinite_plot(plot_object, [[x_axis_variable_name, x_axis[1]], [y_axis_variable_name, y_axis[1]]] + extra_objects, plot_size - 2))

            single_pastplot_width = past_plot_images.get((0, 0)).width
            single_pastplot_height = past_plot_images.get((0, 0)).height

            total_width = single_pastplot_width * amount_of_x_objects_to_generate + x_text_offset
            total_height = single_pastplot_height * amount_of_y_objects_to_generate + y_text_offset

            colorOffset = min(128, 16 * (2 ** ((plot_size - 3) // 2)))
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

    def render(self, plot_object, **kwargs):
        self._prepare_folders(plot_object)

        plot_object.set_do_hash_filenames(kwargs.get("hash_filenames"))
        plot_object.set_cleanup(kwargs.get("cleanup"))

        if kwargs.get("make_html_table") or kwargs.get("make_html_smallplot"):  # We will make the file beforehand so it can be filled dynamically! >:D
            filenames = self._generate_variables_filenames_pairs(plot_object, *plot_object.axises)

            if kwargs.get("make_html_table"):
                renderer = InfiniteRenderer(plot_object, filenames)
                with open("output/{}{}.html".format(plot_object.get_output_folder_name(), plot_object.get_output_file_suffix()), "w", encoding="utf-8") as fstream:
                    fstream.write(renderer.render())

            if kwargs.get("make_html_smallplot"):
                renderer = SmallPlotRenderer(plot_object, filenames)
                with open("output/{}{}.smallplot.html".format(plot_object.get_output_folder_name(), plot_object.get_output_file_suffix()), "w", encoding="utf-8") as fstream:
                    fstream.write(renderer.render())

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
