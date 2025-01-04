from jinja2 import Environment, PackageLoader


class BaseRenderer:
    # I just need to throw this code elsewhere cuz I think it is going to be pretty big and messy when someone more professional gets to tinker with it.
    plotobject = None
    filenames = None
    jinja2renderer = None

    def __init__(self, plot_object, filenames):
        self.plotobject = plot_object
        self.filenames = filenames
        self.jinja2renderer = Environment(loader=PackageLoader("lib", "htmlrenderer_templates"))

        # We should transform filenames (looking like [VAR_1, VAR_2, VAR_3], blabla.png) into IDs (ID1=1, ID2=4) of their axises.

    def search_for_complete_match_names(self, dict_of_names):
        result = ""

        for item in self.filenames:
            if dict_of_names == item[0]:
                result = item[1]

        return result

    def search_for_complete_match_ids(self, dict_of_ids):
        result = ""

        for item in self.filenames:
            if dict_of_ids == item[2]:
                result = item[1]

        return result

    def render(self):
        pass


class InfiniteRenderer(BaseRenderer):
    # Infinite Renderer displays EVERY SINGLE IMAGE AT THE SAME TIME.
    # This way you can see all images, but there is a catch - if you have, like, 4000 images then you will either have to download all of them through network
    # ...AND load all of them into RAM. Not exactly 'good', but works if you have small amount of images.

    def __prerender_image_table(self, extra_objects: dict = None, plot_size=None):
        # Extra Objects should contain ONLY objects down from Axis 3.
        # If plot_size is not specified, then do whatever.
        if plot_size is None:
            plot_size = self.plotobject.get_axis_amount()
        if extra_objects is None:
            extra_objects = dict()

        # Now let's generate our infinite combo wombo
        if plot_size == 1:  # Plot = 1, so one-liner. A unique render.
            x_axisobject = self.plotobject.get_axis_object(0)  # ID: 0, X-Axis.
            x_axis_variable_name = x_axisobject.get_variable_name()

            of_name = self.plotobject.get_output_folder_name()

            # Pregenerate previous tables
            past_plot_image_names = []
            for x_id, _ in enumerate(x_axisobject.get_objects()):
                # Make object name easier to access
                renderedImageName = "{}/{}.png".format(of_name, self.search_for_complete_match_ids({0: x_id}))
                past_plot_image_names.append(renderedImageName)

            # Begin assembling final table
            table = '<table class="plot_depth_1">'

            row_names = ""
            row_tables = ""

            for x_id, x_axis in enumerate(x_axisobject.get_objects()):
                # Paste rows
                row_names += "<td>{} = {}</td>".format(x_axis_variable_name, x_axis)  # Add to name row
                ppin = past_plot_image_names[x_id]
                row_tables += '<td><img class="plot_img" src="{}"></td>'.format(ppin)  # Add to table row a previously rendered table
            table += '<tr class="plot_depth_1">{}</tr><tr class="plot_depth_1">{}</tr>'.format(row_names, row_tables)

            table += "</table>"

            return table
        elif plot_size == 2:  # Plot = 2, so a final XY render.
            x_axisobject = self.plotobject.get_axis_object(0)  # ID: 0, X-Axis.
            x_axis_variable_name = x_axisobject.get_variable_name()
            y_axisobject = self.plotobject.get_axis_object(1)  # ID: 1, Y-Axis.
            y_axis_variable_name = y_axisobject.get_variable_name()

            of_name = self.plotobject.get_output_folder_name()

            past_plot_image_names = dict()
            for x_id, _ in enumerate(x_axisobject.get_objects()):
                for y_id, _ in enumerate(y_axisobject.get_objects()):
                    # Make object name easier to access and to generate normal filename
                    if not extra_objects:
                        all_arguments = {0: x_id, 1: y_id}
                    else:
                        all_arguments = {0: x_id, 1: y_id, **extra_objects}
                    renderedImageName = "{}/{}.png".format(of_name, self.search_for_complete_match_ids(all_arguments))

                    past_plot_image_names.setdefault((x_id, y_id), renderedImageName)

            # Begin assembling final table
            table = '<table class="plot_depth_2">'

            # First, assemble the header row
            table += '<tr class="plot_depth_2">'
            table += "<td></td>"  # The first element is belonging to Y column, therefore empty.
            for _, x_axis in enumerate(x_axisobject.get_objects()):
                table += "<td>{} = {}</td>".format(x_axis_variable_name, x_axis)
            table += "</tr>"

            # Then assemble image rows
            for y_id, y_axis in enumerate(y_axisobject.get_objects()):
                table += '<tr class="plot_depth_2"><td>{} = {}</td>'.format(y_axis_variable_name, y_axis)
                for x_id, x_axis in enumerate(x_axisobject.get_objects()):
                    ppin = past_plot_image_names.get((x_id, y_id))

                    if not extra_objects:
                        all_arguments = {0: x_id, 1: y_id}
                    else:
                        all_arguments = {0: x_id, 1: y_id, **extra_objects}

                    # Render the caption for the image
                    prerendered_caption = list()
                    for argument_axis_id in sorted(all_arguments):
                        axis_object = self.plotobject.get_axis_object(argument_axis_id)
                        axis_name = axis_object.get_variable_name() if isinstance(axis_object.get_variable_name(), str) else " + ".join(axis_object.get_variable_name())
                        axis_value = axis_object.get_object_id(all_arguments[argument_axis_id]) if isinstance(axis_object.get_object_id(all_arguments[argument_axis_id]), str) else " + ".join(axis_object.get_object_id(all_arguments[argument_axis_id]))
                        prerendered_caption.append("{} = {}".format(axis_name, axis_value))
                    rendered_caption = " ||| ".join(prerendered_caption)

                    # Render HTML-arguments for the filter
                    prerendered_filter = list()
                    for argument_axis_id in sorted(all_arguments):
                        prerendered_filter.append('data-axis-id-{}="{}"'.format(argument_axis_id, all_arguments[argument_axis_id]))
                    rendered_filter = " ".join(prerendered_filter)

                    table += '<td><img class="plot_img" src="{}" data-caption="{}" {}></td>'.format(ppin, rendered_caption, rendered_filter)
                table += "</tr>"

            # Finally, close the table.
            table += "</table>"

            return table
        elif plot_size % 2 == 1:  # Plot size is ODD (3, 5, 7). Then it is considered a one-liner of previous iteration.
            x_axisobject = self.plotobject.get_axis_object(plot_size-1)  # ID: Last one, so before it comes XY plot, or XYZW plot, etc...
            x_axis_variable_name = x_axisobject.get_variable_name()

            # Pregenerate previous tables
            past_plot_tables = []
            for x_id, _ in enumerate(x_axisobject.get_objects()):
                past_plot_tables.append(self.__prerender_image_table({plot_size-1: x_id}, plot_size - 1))

            # Begin assembling final table
            table = '<table class="plot_depth_{}">'.format(plot_size)

            row_names = ""
            row_tables = ""

            for x_id, x_axis in enumerate(x_axisobject.get_objects()):
                # Paste rows
                row_names += "<td>{} = {}</td>".format(x_axis_variable_name, x_axis)  # Add to name row
                row_tables += "<td>{}</td>".format(past_plot_tables[x_id])  # Add to table row a previously rendered table
            table += '<tr class="plot_depth_{}">{}</tr><tr class="plot_depth_{}">{}</tr>'.format(plot_size, row_names, plot_size, row_tables)

            table += "</table>"

            return table
        elif plot_size % 2 == 0:  # Plot size is EVEN (4, 6, 8). Then it is considered a XY-plot of previous iteration.
            x_axisobject = self.plotobject.get_axis_object(plot_size-2)  # ID: Almost Last one, so before it comes XY plot, or XYZW plot, etc...
            x_axis_variable_name = x_axisobject.get_variable_name()
            y_axisobject = self.plotobject.get_axis_object(plot_size-1)  # ID: Last one, so before it comes XY plot, or XYZW plot, etc...
            y_axis_variable_name = y_axisobject.get_variable_name()

            past_plot_tables = dict()

            for x_id, x_axis in enumerate(x_axisobject.get_objects()):
                for y_id, y_axis in enumerate(y_axisobject.get_objects()):
                    past_plot_tables.setdefault((x_id, y_id), self.__prerender_image_table({plot_size-2: x_id, plot_size-1: y_id, **extra_objects}, plot_size - 2))

            # Begin assembling final table
            table = '<table class="plot_depth_{}">'.format(plot_size)

            # First, assemble the header row
            table += '<tr class="plot_depth_{}">'.format(plot_size)
            table += "<td></td>"  # The first element is belonging to Y column, therefore empty.
            for x_id, x_axis in enumerate(x_axisobject.get_objects()):
                table += "<td>{} = {}</td>".format(x_axis_variable_name, x_axis)
            table += "</tr>"

            # Then assemble image rows
            for y_id, y_axis in enumerate(y_axisobject.get_objects()):
                table += '<tr class="plot_depth_{}"><td>{} = {}</td>'.format(plot_size, y_axis_variable_name, y_axis)
                for x_id, _ in enumerate(x_axisobject.get_objects()):
                    table += "<td>{}</td>".format(past_plot_tables.get((x_id, y_id)))
                table += "</tr>"

            # Finally, close the table.
            table += "</table>"

            # print("Generation of {}-axis HTML-structure: Ended at {}...".format(plot_size, time.ctime()))
            return table

    def render(self):
        # Load the template of the InfiniteRenderer
        jinja2template = self.jinja2renderer.get_template("infiniterenderer.j2")

        # The thing about the Infinite Grid is that it loads quite slowly, and must be refreshed once in a while
        # But you logically don't want to refresh 10000 images every second. So...
        # 30 secs  if items are 1000 or lower
        # 180 secs if items are higher than 10000
        count_of_generated_objects = 1
        for axis in self.plotobject.axises:
            count_of_generated_objects *= axis.get_object_count()
        seconds_to_wait_on_reloads = int(30 + min(max(0, count_of_generated_objects-1000), 9000)/9000 * 150)

        milliseconds_between_image_reloads = str(seconds_to_wait_on_reloads * 1000)

        # We also need to have good enough sorting function. Probably the easiest way is to compress them.
        # {
        #     axis_id: 0
        #     axis_name: VAR_1
        #     values: [
        #         {
        #             value_id: 0,
        #             value_name: test
        #         }
        #     ]
        # }
        sorting_object = list()
        for axis in self.plotobject.axises:
            axis_id = axis.get_id()
            axis_name = axis.get_variable_name() if isinstance(axis.get_variable_name(), str) else " + ".join(axis.get_variable_name())
            values = list()
            for value_id, value in enumerate(axis.get_objects()):
                value_name = value if isinstance(value, str) else " + ".join(value)
                values.append({"value_id": value_id, "value_name": value_name})
            sorting_object.append({"axis_id": axis_id, "axis_name": axis_name, "values": values})

        # Finally, we need a pre-rendered table with images.
        prerendered_image_table = self.__prerender_image_table()

        argument_list = {
            "RENDER_TITLE": self.plotobject.get_output_folder_name(),
            "PREVIEW_IMAGE_WIDTH": self.plotobject.get_image_width() // 4,
            "PREVIEW_IMAGE_HEIGHT": self.plotobject.get_image_height() // 4,
            "MILLISECONDS_BETWEEN_IMAGE_RELOADS": milliseconds_between_image_reloads,
            "SORTING_OBJECT": sorting_object,
            "PRERENDERED_IMAGE_TABLE": prerendered_image_table
        }

        html_page = jinja2template.render(argument_list)

        return html_page


class SmallPlotRenderer(BaseRenderer):
    def render(self):
        # Load the template of the InfiniteRenderer
        jinja2template = self.jinja2renderer.get_template("smallplotrenderer.j2")

        # We also need to have good enough sorting function. Probably the easiest way is to compress them.
        # {
        #     axis_id: 0
        #     axis_name: VAR_1
        #     values: [
        #         {
        #             value_id: 0,
        #             value_name: test
        #         }
        #     ]
        # }
        sorting_object = list()
        for axis in self.plotobject.axises:
            axis_id = axis.get_id()
            axis_name = axis.get_variable_name() if isinstance(axis.get_variable_name(), str) else " + ".join(axis.get_variable_name())
            values = list()
            for value_id, value in enumerate(axis.get_objects()):
                value_name = value if isinstance(value, str) else " + ".join(value)
                values.append({"value_id": value_id, "value_name": value_name})
            sorting_object.append({"axis_id": axis_id, "axis_name": axis_name, "l_values": values})

        total_file_list = list()
        for item in self.filenames:
            unassembled_file_caption = list()
            for subitem_name, subitem_value in item[0].items():
                unassembled_file_caption.append("{} = {}".format(subitem_name, subitem_value))
            assembled_file_caption = " ||| ".join(unassembled_file_caption)

            total_file_list.append([item[2], item[1], assembled_file_caption])

        # Finally, we need a pre-rendered table with images.
        argument_list = {
            "RENDER_TITLE": self.plotobject.get_output_folder_name(),
            "PREVIEW_IMAGE_WIDTH": self.plotobject.get_image_width() // 2,
            "PREVIEW_IMAGE_HEIGHT": self.plotobject.get_image_height() // 2,
            "OUTPUT_FOLDER_NAME": self.plotobject.get_output_folder_name(),
            "SORTING_OBJECT": sorting_object,
            "TOTAL_FILE_LIST": total_file_list
        }

        html_page = jinja2template.render(argument_list)

        return html_page
