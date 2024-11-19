from lib.plotfile import PlotFile, Axis
from PIL import Image, ImageDraw, ImageFont
from comfyui_api import ComfyUIAPI
from lib.filename_sanitizer import sanitize_filename

import os
import time


class PlotFileRenderer:
    capi = None

    def __init__(self, comfyui_api) -> None:
        if not isinstance(comfyui_api, ComfyUIAPI):
            raise Exception("Cannot initalize PlotFileRenderer - no ComfyUIAPI object provided.")
        self.capi = comfyui_api

    def _prepare_folders(self, plot_object):
        os.makedirs("{}/{}".format("output", plot_object.get_output_folder_name()), exist_ok=True)

    def _generate_filename_for_image(self, item: list) -> str:
        filename = "img"
        for variable_content in item:
            if isinstance(variable_content, list) or isinstance(variable_content, tuple):
                filename += "_"
                for subvariable_content in variable_content:
                    filename += "_" + subvariable_content
            else:
                filename += "__" + variable_content
        return sanitize_filename(filename)

    def _render_all_images(self, plot_object, *axis_objects):
        print("Generation/Rendering: Started at {}...".format(time.ctime()))

        # Just a preflight checks...
        for axis_object in axis_objects:
            if not isinstance(axis_object, Axis):
                raise Exception("_render_all_images received a non-axis object {} - script shutdowned".format(axis_object))

        # Some variables for convinience
        of_name = plot_object.get_output_folder_name()

        # Make a huge list of objects.
        pools = [tuple(axis_object.get_objects()) for axis_object in axis_objects]

        all_variables_possible_to_generate = [[]]
        for pool in pools:
            all_variables_possible_to_generate = [x+[y] for x in all_variables_possible_to_generate for y in pool]

        # Turn this huge list into a list of [VARIABLES_DICT, FILENAME].
        all_variable_names_possible = [axis_object.get_variable_name() for axis_object in axis_objects]

        all_items_to_generate = list()
        for item_to_generate in all_variables_possible_to_generate:
            variables = dict()
            for variable_name in enumerate(all_variable_names_possible):
                if isinstance(variable_name[1], list):  # If it is list, then consider going in recursively
                    for subvariable_name in enumerate(variable_name[1]):
                        variables.setdefault(subvariable_name[1], item_to_generate[variable_name[0]][subvariable_name[0]])
                else:  # Else treat it as string
                    variables.setdefault(variable_name[1], item_to_generate[variable_name[0]])
            all_items_to_generate.append((variables, self._generate_filename_for_image(item_to_generate)))

        # Finally, generate all images.
        # ...also track time, just for convinience.
        current_timestamp = time.time()
        current_progress = 0
        maximum_progress = len(all_items_to_generate)
        
        print("Preparing to generate {} images...".format(maximum_progress))

        for item_to_generate in all_items_to_generate:
            imagepath = "output/{}/{}.png".format(of_name, item_to_generate[1])
            if os.path.exists(imagepath):
                print("{} exists, skipping generation.".format(item_to_generate[1]))
            else:
                rendered_workflow = plot_object.generate_workflow(item_to_generate[0])
                self.capi.generate_image(rendered_workflow, imagepath)

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

    def make_x_plot(self, plot_object: PlotFile):
        # Width of 1-axis render is a width of image * amount of images
        # Height of 1-axis render is a height of image + 200 pixels for text
        print("Generation of 1-axis (X-only) structure: Started at {}...".format(time.ctime()))

        axisobject = plot_object.get_axis_object(0)  # ID: 0, X-Axis.
        axis_variable_name = axisobject.get_variable_name()

        single_image_width = plot_object.get_image_width()
        single_image_height = plot_object.get_image_height()

        y_text_offset = 200

        if plot_object.get_resize_ratio() is not None:
            single_image_width = int(single_image_width * plot_object.get_resize_ratio())
            single_image_height = int(single_image_height * plot_object.get_resize_ratio())
            y_text_offset = int(200 * plot_object.get_resize_ratio())

        total_width = single_image_width * axisobject.get_object_count()
        total_height = single_image_height + y_text_offset

        of_name = plot_object.get_output_folder_name()

        # Make empty image
        imageObject = Image.new("RGB", (total_width, total_height), (255, 128, 0))

        for x_axis in enumerate(axisobject.get_objects()):
            # Make object name easier to access
            renderedImageName = "output/{}/{}.png".format(of_name, self._generate_filename_for_image((x_axis[1],)))

            # Paste image with specific offsets
            self._paste_image(imageObject, renderedImageName, x_axis[0]*single_image_width, y_text_offset, plot_object.get_resize_ratio())

            # Generate label for image.
            pos_bbox = (x_axis[0]*single_image_width, 0, x_axis[0]*single_image_width + single_image_width, y_text_offset)
            self._make_label(imageObject, pos_bbox, axis_variable_name, x_axis[1])

        print("Generation of 1-axis (X-only) structure: Ended at {}...".format(time.ctime()))
        return imageObject

    def make_xy_plot(self, plot_object: PlotFile, *extra_objects):
        # A bit more complicated, but still fine enough
        # Width of 2-axis render is a width of image * amount of images on X axis + 400 pixels for text
        # Height of 2-axis render is a height of image * amount of images on Y axis + 200 pixels for text
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
                all_arguments = [x_axis[1], y_axis[1]] + list(extra_objects)
                renderedImageName = "output/{}/{}.png".format(of_name, self._generate_filename_for_image(all_arguments))

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

    def make_infinite_plot(self, plot_object: PlotFile, extra_objects: list = None, plot_size = None):
        # Extra Objects should contain ONLY objects down from Axis 3.
        # If plot_size is not specified, then do whatever.
        if plot_size is None:
            plot_size = plot_object.get_axis_amount()
        if extra_objects is None:
            extra_objects = list()

        # Now let's generate our infinite combo wombo
        if plot_size == 1:  # Plot = 1, so one-liner. A unique render.
            return self.make_x_plot(plot_object)
        elif plot_size == 2:  # Plot = 2, so a final XY render.
            return self.make_xy_plot(plot_object, *extra_objects)
        elif plot_size % 2 == 1:  # Plot size is ODD (3, 5, 7). Then it is considered a one-liner of previous iteration.
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
                past_plot_images.append(self.make_infinite_plot(plot_object, [x_axis[1]] + extra_objects, plot_size - 1))
            
            single_pastplot_width = past_plot_images[0].width
            single_pastplot_height = past_plot_images[0].height
            colorOffset = min(128, 16 * (2 ** ( (plot_size - 3) // 2 ) ))

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
        elif plot_size % 2 == 0:  # Plot size is EVEN (4, 6, 8). Then it is considered a XY-plot of previous iteration.
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
                    past_plot_images.setdefault((x_axis[0], y_axis[0]), self.make_infinite_plot(plot_object, [x_axis[1], y_axis[1]] + extra_objects, plot_size - 2))
            
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

    def render(self, plot_object, **kwargs):
        self._prepare_folders(plot_object)
        self._render_all_images(plot_object, *plot_object.axises)
        if not kwargs.get("skip_mass_generation"):
            if "resize_ratio" in kwargs:
                plot_object.set_resize_ratio(kwargs.get("resize_ratio", 1.0))

            plot_object.set_ignore_non_replacements(kwargs.get("ignore_non_replacements"))
            plot_object.set_flip_last_axis(kwargs.get("flip_last_axis"))

            image = self.make_infinite_plot(plot_object)    

            if "autoreduce" in kwargs:
                if image.width > kwargs.get("autoreduce") or image.height > kwargs.get("autoreduce"):
                    maxsize = max(image.width, image.height)
                    print("Autoreduce kicked in since one of the dimensions of image is {} out of {}...".format(maxsize, kwargs.get("autoreduce")))
                    newratio = kwargs.get("autoreduce") / maxsize
                    image = image.resize((int(image.width*newratio), int(image.height*newratio)))

            image.save("output/{}{}.png".format(plot_object.get_output_folder_name(), plot_object.get_output_file_suffix()))
        
        input("Render completed. Press ENTER to exit the script.")
