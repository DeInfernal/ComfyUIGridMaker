import yaml
import json


class Axis:
    variablename = None
    objects = None
    order = None
    
    def __lt__(self, other):
        return self.get_sorting_variable_name() < other.get_sorting_variable_name()
    
    def __init__(self, axis_object):
        if "replace" not in axis_object:
            raise Exception("In description of axis {} I cannot find 'replace' (string type, Variable name to search) object.".format(axis_object))
        if "with" not in axis_object:
            raise Exception("In description of axis {} I cannot find 'with' (array of string type, Variable name to replace) object.".format(axis_object))
        self.variablename = axis_object.get("replace")
        self.objects = axis_object.get("with")
        self.order = axis_object.get("order", 0)

    def get_variable_name(self):
        return self.variablename

    def get_sorting_variable_name(self):
        return self.variablename if isinstance(self.variablename, str) else self.variablename[0]

    def get_objects(self):
        return self.objects

    def get_object_count(self):
        return len(self.objects)

    def get_order(self):
        return self.order

class PlotFile:
    content = None
    workflow_stencil = None
    axises = None
    variables = None
    system_variables = None
    output_folder_name = None
    output_file_suffix = None
    resize_ratio = None
    ignore_non_replacements = False
    flip_last_axis = False
    autoflip_last_axis = False
    do_hash_filenames = False
    cleanup = False
    
    def __init__(self, plotfile_path):
        with open(plotfile_path, "r", encoding="utf-8") as fstream:
            self.content = yaml.safe_load(fstream)
        
        if not isinstance(self.content, dict):
            raise Exception("PlotFile is not a dictionary object.")

        if "Axises" not in self.content:
            raise Exception("A correct Axises must be present in PlotFile.")
        self.axises = list()
        for axis in self.content.get("Axises"):
            self.axises.append(Axis(axis))

        if "Variables" not in self.content:
            print("Variables dictionary not found - making it empty.")
        self.variables = self.content.get("Variables", dict())
        self.system_variables = dict()

        if "Image_Width" not in self.content:
            raise Exception("A correct Image_Width must be present in PlotFile.")
        self.system_variables.setdefault("IMAGE_WIDTH", self.content.get("Image_Width"))
        self.system_variables.setdefault("IMAGE_ONEANDATHIRDOFHALVED_WIDTH", int(self.content.get("Image_Width")*0.66))
        self.system_variables.setdefault("IMAGE_ONEANDAHALFOFHALVED_WIDTH", int(self.content.get("Image_Width")*0.75))
        self.system_variables.setdefault("IMAGE_ONEANDTWOTHIRDSOFHALVED_WIDTH", int(self.content.get("Image_Width")*0.83))
        self.system_variables.setdefault("IMAGE_ONEANDATHIRD_WIDTH", int(self.content.get("Image_Width")*1.33))
        self.system_variables.setdefault("IMAGE_ONEANDTWOTHIRDS_WIDTH", int(self.content.get("Image_Width")*1.66))
        self.system_variables.setdefault("IMAGE_ONEANDAHALF_WIDTH", int(self.content.get("Image_Width")*1.5))
        self.system_variables.setdefault("IMAGE_DOUBLE_WIDTH", self.content.get("Image_Width")*2)
        self.system_variables.setdefault("IMAGE_QUAD_WIDTH", self.content.get("Image_Width")*4)
        self.system_variables.setdefault("IMAGE_HALF_WIDTH", int(self.content.get("Image_Width")/2))
        self.system_variables.setdefault("IMAGE_QUARTER_WIDTH", int(self.content.get("Image_Width")/4))

        if "Image_Height" not in self.content:
            raise Exception("A correct Image_Height must be present in PlotFile.")
        self.system_variables.setdefault("IMAGE_HEIGHT", self.content.get("Image_Height"))
        self.system_variables.setdefault("IMAGE_ONEANDATHIRDOFHALVED_HEIGHT", int(self.content.get("Image_Height")*0.66))
        self.system_variables.setdefault("IMAGE_ONEANDAHALFOFHALVED_HEIGHT", int(self.content.get("Image_Height")*0.75))
        self.system_variables.setdefault("IMAGE_ONEANDTWOTHIRDSOFHALVED_HEIGHT", int(self.content.get("Image_Height")*0.83))
        self.system_variables.setdefault("IMAGE_ONEANDATHIRD_HEIGHT", int(self.content.get("Image_Height")*1.33))
        self.system_variables.setdefault("IMAGE_ONEANDTWOTHIRDS_HEIGHT", int(self.content.get("Image_Height")*1.66))
        self.system_variables.setdefault("IMAGE_ONEANDAHALF_HEIGHT", int(self.content.get("Image_Height")*1.5))
        self.system_variables.setdefault("IMAGE_DOUBLE_HEIGHT", self.content.get("Image_Height")*2)
        self.system_variables.setdefault("IMAGE_QUAD_HEIGHT", self.content.get("Image_Height")*4)
        self.system_variables.setdefault("IMAGE_HALF_HEIGHT", int(self.content.get("Image_Height")/2))
        self.system_variables.setdefault("IMAGE_QUARTER_HEIGHT", int(self.content.get("Image_Height")/4))

        if "OutputFolderName" not in self.content:
            print("No OutputFolderName present in PlotFile. Outputing results into folder named 'Generic'")
        self.output_folder_name = self.content.get("OutputFolderName", "Generic")
        self.system_variables.setdefault("OUTPUT_FOLDER_NAME", self.output_folder_name)

        if "OutputFileSuffix" not in self.content:
            print("No OutputFileSuffix present in PlotFile. It is set to None.")
        self.output_file_suffix = self.content.get("OutputFileSuffix", "")
        self.system_variables.setdefault("OUTPUT_FILE_SUFFIX", self.output_file_suffix)

        if "WorkflowPath" not in self.content:
            raise Exception("A correct WorkflowPath must be present in PlotFile.")
        with open(self.content.get("WorkflowPath"), "r", encoding="utf-8") as fstream:
            self.workflow_stencil = fstream.read()

    def get_output_folder_name(self):
        return self.output_folder_name

    def get_output_file_suffix(self):
        return self.output_file_suffix

    def get_image_width(self):
        return self.content.get("Image_Width")

    def get_image_height(self):
        return self.content.get("Image_Height")

    def get_axis_amount(self):
        return len(self.axises)

    def get_axis_object(self, axis_id):
        return self.axises[axis_id]

    def get_axis_objects(self, axis_id):
        return self.axises[axis_id].get_objects()

    def get_axis_objects_count(self, axis_id):
        return self.axises[axis_id].get_object_count()

    def get_resize_ratio(self):
        return self.resize_ratio

    def set_resize_ratio(self, new_ratio):
        self.resize_ratio = new_ratio

    def get_ignore_non_replacements(self):
        return self.ignore_non_replacements

    def set_ignore_non_replacements(self, new_ignore_non_replacements):
        self.ignore_non_replacements = new_ignore_non_replacements

    def get_flip_last_axis(self):
        return self.flip_last_axis

    def set_flip_last_axis(self, new_flip_last_axis):
        self.flip_last_axis = new_flip_last_axis

    def get_autoflip_last_axis(self):
        return self.autoflip_last_axis

    def set_autoflip_last_axis(self, new_autoflip_last_axis):
        self.autoflip_last_axis = new_autoflip_last_axis
        
    def get_do_hash_filenames(self):
        return self.do_hash_filenames

    def set_do_hash_filenames(self, new_do_hash_filenames):
        self.do_hash_filenames = new_do_hash_filenames

    def get_cleanup(self):
        return self.cleanup

    def set_cleanup(self, new_cleanup):
        self.cleanup = new_cleanup

    def _replace_system_variables(self, string_workflow):
        replacement_amount = 0
        resulting_string_workflow = string_workflow

        for variable in self.system_variables:
            new_string_workflow = resulting_string_workflow.replace(variable, str(self.system_variables.get(variable)))
            if new_string_workflow != resulting_string_workflow:
                replacement_amount += 1
            resulting_string_workflow = new_string_workflow
        
        return resulting_string_workflow, replacement_amount

    def _replace_static_variables(self, string_workflow):
        replacement_amount = 0
        resulting_string_workflow = string_workflow

        for variable in self.variables:
            new_string_workflow = resulting_string_workflow.replace(variable, str(self.variables.get(variable)))
            if new_string_workflow != resulting_string_workflow:
                replacement_amount += 1
            resulting_string_workflow = new_string_workflow
        
        return resulting_string_workflow, replacement_amount

    def _replace_dynamic_variables(self, string_workflow, values: dict):
        replacement_amount = 0
        resulting_string_workflow = string_workflow

        for value in values:
            new_string_workflow = resulting_string_workflow.replace(value, str(values.get(value)))
            if new_string_workflow != resulting_string_workflow:
                replacement_amount += 1
            resulting_string_workflow = new_string_workflow
        
        return resulting_string_workflow, replacement_amount

    def _replace_all_variables(self, string_workflow, values: dict):
        t_string_workflow, firstrepl = self._replace_system_variables(string_workflow)
        t_string_workflow, secondrepl = self._replace_static_variables(string_workflow)
        t_string_workflow, thirdrepl = self._replace_dynamic_variables(t_string_workflow, values)
        return t_string_workflow, firstrepl + secondrepl + thirdrepl

    def generate_workflow(self, values: dict):
        string_workflow = self.workflow_stencil
        # Initially replace system variables. It is okay if nothing gets replaced, since not every system variable is used.
        string_workflow, _ = self._replace_system_variables(string_workflow)

        # Initially replace static variables.
        for variable in self.variables:
            new_string_workflow = string_workflow.replace(variable, str(self.variables.get(variable)))
            
            if not self.ignore_non_replacements and new_string_workflow == string_workflow:
                print("ERROR! HALT! ERROR! HALT! ERROR! HALT!")
                print("HALT! ERROR! HALT! ERROR! HALT! ERROR!")
                print("ERROR! HALT! ERROR! HALT! ERROR! HALT!")
                print()
                print("After initial replacing {} static/Axis variable, no changes were made to the workflow!".format(variable))
                print("This indicates that something is wrong with the Plotfile.")
                print("Please recheck the plotfile manually.")
                print("If this is desired behavior, run the script")
                print("with flag --ignore_non_replacements .")
                print()
                input("Press enter to exit program.")
                exit(0)
                
            string_workflow = new_string_workflow

        # Initially replace dynamic variables.
        for value in values:
            new_string_workflow = string_workflow.replace(value, str(values.get(value)))

            if not self.ignore_non_replacements and new_string_workflow == string_workflow:
                print("ERROR! HALT! ERROR! HALT! ERROR! HALT!")
                print("HALT! ERROR! HALT! ERROR! HALT! ERROR!")
                print("ERROR! HALT! ERROR! HALT! ERROR! HALT!")
                print()
                print("After initial replacing {} dynamic/Axis variable, no changes were made to the workflow!".format(value))
                print("This indicates that something is wrong with the Plotfile.")
                print("Please recheck the plotfile manually.")
                print("If this is desired behavior, run the script")
                print("with flag --ignore_non_replacements .")
                print()
                input("Press enter to exit program.")
                exit(0)

            string_workflow = new_string_workflow

        # Start replacing variables recursively until either no replacements are made or replacements exceeded threshold of 128
        replacement_cycles = 0
        string_workflow, last_replacement_count = self._replace_all_variables(string_workflow, values)
        while replacement_cycles < 128 and last_replacement_count > 0:
            replacement_cycles += 1
            string_workflow, last_replacement_count = self._replace_all_variables(string_workflow, values)
        
        if replacement_cycles > 127:
            print("ERROR! HALT! ERROR! HALT! ERROR! HALT!")
            print("HALT! ERROR! HALT! ERROR! HALT! ERROR!")
            print("ERROR! HALT! ERROR! HALT! ERROR! HALT!")
            print()
            print("After cycling replacmement of 127 cycles, script still found something to replace")
            print("This indicates recursive replacement somewhere. Fix it manually.")
            print()
            input("Press enter to exit program.")
            exit(0) 

        # Render workflow.
        # print(string_workflow)  # Debugging purposes
        rendered_workflow = json.loads(string_workflow)

        # Return generated workflow.
        return rendered_workflow
