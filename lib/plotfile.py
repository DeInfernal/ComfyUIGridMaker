import yaml
import json


class Axis:
    variablename = None
    objects = None
    
    def __init__(self, axis_object):
        if "replace" not in axis_object:
            raise Exception("In description of axis {} I cannot find 'replace' (string type, Variable name to search) object.".format(axis_object))
        if "with" not in axis_object:
            raise Exception("In description of axis {} I cannot find 'with' (array of string type, Variable name to replace) object.".format(axis_object))
        self.variablename = axis_object.get("replace")
        self.objects = axis_object.get("with")

    def get_variable_name(self):
        return self.variablename

    def get_objects(self):
        return self.objects

    def get_object_count(self):
        return len(self.objects)

class PlotFile:
    content = None
    workflow_stencil = None
    axises = None
    variables = None
    output_folder_name = None
    
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

        if "Image_Width" not in self.content:
            raise Exception("A correct Image_Width must be present in PlotFile.")
        self.variables.setdefault("IMAGE_WIDTH", self.content.get("Image_Width"))

        if "Image_Height" not in self.content:
            raise Exception("A correct Image_Height must be present in PlotFile.")
        self.variables.setdefault("IMAGE_HEIGHT", self.content.get("Image_Height"))

        if "OutputFolderName" not in self.content:
            print("No OutputFolderName present in PlotFile. Outputing results into folder named 'Generic'")
        self.output_folder_name = self.content.get("OutputFolderName", "Generic")
        self.variables.setdefault("OUTPUT_FOLDER_NAME", self.output_folder_name)

        if "WorkflowPath" not in self.content:
            raise Exception("A correct WorkflowPath must be present in PlotFile.")
        with open(self.content.get("WorkflowPath"), "r", encoding="utf-8") as fstream:
            self.workflow_stencil = fstream.read()

    def get_output_folder_name(self):
        return self.output_folder_name

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

    def generate_workflow(self, values: dict):
        string_workflow = self.workflow_stencil
        # Replace static variables.
        for variable in self.variables:
            string_workflow = string_workflow.replace(variable, str(self.variables.get(variable)))

        # Replace dynamic variables.
        for value in values:
            string_workflow = string_workflow.replace(value, str(values.get(value)))

        # Render workflow.
        rendered_workflow = json.loads(string_workflow)

        # Return generated workflow.
        return rendered_workflow
