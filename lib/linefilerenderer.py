from lib.linefile import LineFile, Slider
from PIL import Image
from comfyui_api import ComfyUIAPI

import os
import time

import apng
import cv2
import numpy as np


class LineFileRenderer:
    capi = None

    def __init__(self, comfyui_api) -> None:
        if not isinstance(comfyui_api, ComfyUIAPI):
            raise Exception("Cannot initalize LineFileRenderer - no ComfyUIAPI object provided.")
        self.capi = comfyui_api

    def _prepare_folders(self, line_object: LineFile):
        os.makedirs("{}/{}".format("output", line_object.get_output_folder_name()), exist_ok=True)

    def _clone_workflowstate(self, workflow_state):
        new_workflow_state = dict()
        for item in workflow_state:
            if isinstance(workflow_state.get(item), float):
                new_value = "{:6f}".format(workflow_state.get(item))
                if new_value == "-0.000000":
                    new_value = "0.0"
                new_workflow_state.setdefault(item, new_value)
            else:
                new_workflow_state.setdefault(item, str(workflow_state.get(item)))
        return new_workflow_state

    def _render_all_images(self, line_object: LineFile, *sliders_objects):
        print("Generation/Rendering: Started at {}...".format(time.ctime()))

        # Just a preflight checks...
        for slider_object in sliders_objects:
            if not isinstance(slider_object, Slider):
                raise Exception("_render_all_images received a non-slider object {} - script shutdowned".format(slider_object))

        # Some variables for convinience
        of_name = line_object.get_output_folder_name()

        # Build initial workflow state
        workflow_state = line_object.get_initial_workflow_state()

        # Build queue of images and fill it with first image
        image_queue = list()
        image_queue.append(self._clone_workflowstate(workflow_state))

        # Now go and make each slider slide.
        for slider in sliders_objects:
            current_varname = slider.get_variable_name()
            current_from = workflow_state.get(current_varname)
            list_of_frames = slider.compile(current_from, line_object.get_fps())
            for frame in list_of_frames:
                workflow_state[current_varname] = frame
                image_queue.append(self._clone_workflowstate(workflow_state))

        # Finally, generate all images.
        # ...also track time, just for convinience.
        current_timestamp = time.time()
        current_progress = 0
        maximum_progress = len(image_queue)

        print("Preparing to generate {} images...".format(maximum_progress))

        for item_to_generate in enumerate(image_queue):
            imgnumber = str(item_to_generate[0]).zfill(8)
            imagepath = "output/{}/{}.png".format(of_name, imgnumber)
            if os.path.exists(imagepath):
                print("! {}".format(imgnumber))
            else:
                rendered_workflow = line_object.generate_workflow(item_to_generate[1])
                self.capi.generate_image(rendered_workflow, imagepath)
                print("+ {}".format(imgnumber))
            if line_object.debug:
                print("--- {}".format(item_to_generate))

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

    def render(self, line_object: LineFile, **kwargs):
        self._prepare_folders(line_object)
        line_object.debug = kwargs.get("debug")
        line_object.set_fps(kwargs.get("fps"))
        line_object.set_ignore_non_replacements(kwargs.get("ignore_non_replacements"))

        if not kwargs.get("skip_rendering"):
            self._render_all_images(line_object, *line_object.sliders)

        if not kwargs.get("skip_compilation"):
            if "resize_ratio" in kwargs:
                line_object.set_resize_ratio(kwargs.get("resize_ratio", 1.0))

            if "apng" in kwargs.get("output_type"):
                apng_image = apng.APNG()
                delay_time = int(1000 / line_object.get_fps())
                ofname = line_object.get_output_folder_name()
                images_folder = "{}/{}".format("output", ofname)
                list_of_images = os.listdir(images_folder)
                apng_image.append_file("{}/{}/{}".format("output", ofname, list_of_images[0]), delay=4000)
                for image_path in list_of_images[1:-1]:
                    apng_image.append_file("{}/{}/{}".format("output", ofname, image_path), delay=delay_time)
                apng_image.append_file("{}/{}/{}".format("output", ofname, list_of_images[-1]), delay=4000)
                if kwargs.get("do_reverse"):
                    for image_path in reversed(list_of_images[1:-1]):
                        apng_image.append_file("{}/{}/{}".format("output", ofname, image_path), delay=delay_time)
                apng_image.save("{}/{}.png".format("output", ofname))

            if "webp" in kwargs.get("output_type"):
                images = list()
                durations = list()
                delay_time = int(1000 / line_object.get_fps())
                ofname = line_object.get_output_folder_name()
                images_folder = "{}/{}".format("output", ofname)
                list_of_images = os.listdir(images_folder)

                images.append(Image.open("{}/{}/{}".format("output", ofname, list_of_images[0])))
                durations.append(4000)

                for image_path in list_of_images[1:-1]:
                    images.append(Image.open("{}/{}/{}".format("output", ofname, image_path)))
                    durations.append(delay_time)

                images.append(Image.open("{}/{}/{}".format("output", ofname, list_of_images[-1])))
                durations.append(4000)

                if kwargs.get("do_reverse"):
                    for image_path in reversed(list_of_images[1:-1]):
                        images.append(Image.open("{}/{}/{}".format("output", ofname, image_path)))
                        durations.append(delay_time)

                images[0].save("{}/{}.webp".format("output", ofname), save_all=True, append_images=images[1:], duration=durations, loop=0)

            if "webp_averaged1" in kwargs.get("output_type"):
                images = list()
                durations = list()
                delay_time = int(1000 / line_object.get_fps())
                ofname = line_object.get_output_folder_name()
                images_folder = "{}/{}".format("output", ofname)
                list_of_images = os.listdir(images_folder)

                # Prepare averaged images first
                averaged_images = []
                averaging_radius = 1
                for i in range(len(list_of_images)):
                    start = max(0, i - averaging_radius)
                    end = min(len(list_of_images), i + averaging_radius + 1)
                    images_to_combine = [np.asarray(Image.open("{}/{}/{}".format("output", ofname, list_of_images[j]))) for j in range(start, end)]
                    averaged_image = np.mean(images_to_combine, axis=0).astype(np.uint8)
                    averaged_images.append(Image.fromarray(averaged_image))

                images.append(Image.open("{}/{}/{}".format("output", ofname, list_of_images[0])))
                durations.append(4000)

                for image_object in averaged_images:
                    images.append(image_object)
                    durations.append(delay_time)

                images.append(Image.open("{}/{}/{}".format("output", ofname, list_of_images[-1])))
                durations.append(4000)

                if kwargs.get("do_reverse"):
                    for image_object in reversed(averaged_images):
                        images.append(image_object)
                        durations.append(delay_time)

                images[0].save("{}/{}_averaged1.webp".format("output", ofname), save_all=True, append_images=images[1:], duration=durations, loop=0)

            if "webp_averaged2" in kwargs.get("output_type"):
                images = list()
                durations = list()
                delay_time = int(1000 / line_object.get_fps())
                ofname = line_object.get_output_folder_name()
                images_folder = "{}/{}".format("output", ofname)
                list_of_images = os.listdir(images_folder)

                # Prepare averaged images first
                averaged_images = []
                averaging_radius = 2
                for i in range(len(list_of_images)):
                    start = max(0, i - averaging_radius)
                    end = min(len(list_of_images), i + averaging_radius + 1)
                    images_to_combine = [np.asarray(Image.open("{}/{}/{}".format("output", ofname, list_of_images[j]))) for j in range(start, end)]
                    averaged_image = np.mean(images_to_combine, axis=0).astype(np.uint8)
                    averaged_images.append(Image.fromarray(averaged_image))

                images.append(Image.open("{}/{}/{}".format("output", ofname, list_of_images[0])))
                durations.append(4000)

                for image_object in averaged_images:
                    images.append(image_object)
                    durations.append(delay_time)

                images.append(Image.open("{}/{}/{}".format("output", ofname, list_of_images[-1])))
                durations.append(4000)

                if kwargs.get("do_reverse"):
                    for image_object in reversed(averaged_images):
                        images.append(image_object)
                        durations.append(delay_time)

                images[0].save("{}/{}_averaged2.webp".format("output", ofname), save_all=True, append_images=images[1:], duration=durations, loop=0)

            if "webp_averaged3" in kwargs.get("output_type"):
                images = list()
                durations = list()
                delay_time = int(1000 / line_object.get_fps())
                ofname = line_object.get_output_folder_name()
                images_folder = "{}/{}".format("output", ofname)
                list_of_images = os.listdir(images_folder)

                # Prepare averaged images first
                averaged_images = []
                averaging_radius = 3
                for i in range(len(list_of_images)):
                    start = max(0, i - averaging_radius)
                    end = min(len(list_of_images), i + averaging_radius + 1)

                    images_to_combine = [np.asarray(Image.open("{}/{}/{}".format("output", ofname, list_of_images[j]))) for j in range(start, end)]
                    averaged_image = np.mean(images_to_combine, axis=0).astype(np.uint8)
                    averaged_images.append(Image.fromarray(averaged_image))

                images.append(Image.open("{}/{}/{}".format("output", ofname, list_of_images[0])))
                durations.append(4000)

                for image_object in averaged_images:
                    images.append(image_object)
                    durations.append(delay_time)

                images.append(Image.open("{}/{}/{}".format("output", ofname, list_of_images[-1])))
                durations.append(4000)

                if kwargs.get("do_reverse"):
                    for image_object in reversed(averaged_images):
                        images.append(image_object)
                        durations.append(delay_time)

                images[0].save("{}/{}_averaged3.webp".format("output", ofname), save_all=True, append_images=images[1:], duration=durations, loop=0)

            if "mp4" in kwargs.get("output_type"):
                ofname = line_object.get_output_folder_name()
                fps = kwargs.get("fps")
                images_folder = "{}/{}".format("output", ofname)
                list_of_images = os.listdir(images_folder)
                outputfilename = "{}/{}.mp4".format("output", ofname)
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(outputfilename, fourcc, fps, (line_object.get_image_width(), line_object.get_image_height()))

                img = cv2.imread("{}/{}/{}".format("output", ofname, list_of_images[0]))
                for _ in range(4 * fps):
                    video_writer.write(img)

                for image_path in list_of_images[1:-1]:
                    img = cv2.imread("{}/{}/{}".format("output", ofname, image_path))
                    video_writer.write(img)

                img = cv2.imread("{}/{}/{}".format("output", ofname, list_of_images[-1]))
                for _ in range(4 * fps):
                    video_writer.write(img)

                if kwargs.get("do_reverse"):
                    for image_path in reversed(list_of_images[1:-1]):
                        img = cv2.imread("{}/{}/{}".format("output", ofname, image_path))
                        video_writer.write(img)

                video_writer.release()

            if "mp4_averaged1" in kwargs.get("output_type"):
                ofname = line_object.get_output_folder_name()
                fps = kwargs.get("fps")
                images_folder = "{}/{}".format("output", ofname)
                list_of_images = os.listdir(images_folder)
                outputfilename = "{}/{}_averaged1.mp4".format("output", ofname)
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(outputfilename, fourcc, fps, (line_object.get_image_width(), line_object.get_image_height()))

                # Prepare averaged images first
                averaged_images = []
                averaging_radius = 1
                for i in range(len(list_of_images)):
                    start = max(0, i - averaging_radius)
                    end = min(len(list_of_images), i + averaging_radius + 1)
                    images_to_combine = [cv2.imread("{}/{}/{}".format("output", ofname, list_of_images[j])) for j in range(start, end)]
                    averaged_image = np.mean(images_to_combine, axis=0).astype(np.uint8)
                    averaged_images.append(averaged_image)

                img = cv2.imread("{}/{}/{}".format("output", ofname, list_of_images[0]))
                for _ in range(4 * fps):
                    video_writer.write(img)

                for image_file in averaged_images:
                    video_writer.write(image_file)

                img = cv2.imread("{}/{}/{}".format("output", ofname, list_of_images[-1]))
                for _ in range(4 * fps):
                    video_writer.write(img)

                if kwargs.get("do_reverse"):
                    for image_file in reversed(averaged_images):
                        video_writer.write(image_file)

                video_writer.release()

            if "mp4_averaged2" in kwargs.get("output_type"):
                ofname = line_object.get_output_folder_name()
                fps = kwargs.get("fps")
                images_folder = "{}/{}".format("output", ofname)
                list_of_images = os.listdir(images_folder)
                outputfilename = "{}/{}_averaged2.mp4".format("output", ofname)
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(outputfilename, fourcc, fps, (line_object.get_image_width(), line_object.get_image_height()))

                # Prepare averaged images first
                averaged_images = []
                averaging_radius = 2
                for i in range(len(list_of_images)):
                    start = max(0, i - averaging_radius)
                    end = min(len(list_of_images), i + averaging_radius + 1)
                    images_to_combine = [cv2.imread("{}/{}/{}".format("output", ofname, list_of_images[j])) for j in range(start, end)]
                    averaged_image = np.mean(images_to_combine, axis=0).astype(np.uint8)
                    averaged_images.append(averaged_image)

                img = cv2.imread("{}/{}/{}".format("output", ofname, list_of_images[0]))
                for _ in range(4 * fps):
                    video_writer.write(img)

                for image_file in averaged_images:
                    video_writer.write(image_file)

                img = cv2.imread("{}/{}/{}".format("output", ofname, list_of_images[-1]))
                for _ in range(4 * fps):
                    video_writer.write(img)

                if kwargs.get("do_reverse"):
                    for image_file in reversed(averaged_images):
                        video_writer.write(image_file)

                video_writer.release()

            if "mp4_averaged3" in kwargs.get("output_type"):
                ofname = line_object.get_output_folder_name()
                fps = kwargs.get("fps")
                images_folder = "{}/{}".format("output", ofname)
                list_of_images = os.listdir(images_folder)
                outputfilename = "{}/{}_averaged3.mp4".format("output", ofname)
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(outputfilename, fourcc, fps, (line_object.get_image_width(), line_object.get_image_height()))

                # Prepare averaged images first
                averaged_images = []
                averaging_radius = 3
                for i in range(len(list_of_images)):
                    start = max(0, i - averaging_radius)
                    end = min(len(list_of_images), i + averaging_radius + 1)
                    images_to_combine = [cv2.imread("{}/{}/{}".format("output", ofname, list_of_images[j])) for j in range(start, end)]
                    averaged_image = np.mean(images_to_combine, axis=0).astype(np.uint8)
                    averaged_images.append(averaged_image)

                img = cv2.imread("{}/{}/{}".format("output", ofname, list_of_images[0]))
                for _ in range(4 * fps):
                    video_writer.write(img)

                for image_file in averaged_images:
                    video_writer.write(image_file)

                img = cv2.imread("{}/{}/{}".format("output", ofname, list_of_images[-1]))
                for _ in range(4 * fps):
                    video_writer.write(img)

                if kwargs.get("do_reverse"):
                    for image_file in reversed(averaged_images):
                        video_writer.write(image_file)

                video_writer.release()

            if "webm" in kwargs.get("output_type"):
                ofname = line_object.get_output_folder_name()
                fps = kwargs.get("fps")
                images_folder = "{}/{}".format("output", ofname)
                list_of_images = os.listdir(images_folder)
                outputfilename = "{}/{}.webm".format("output", ofname)
                fourcc = cv2.VideoWriter_fourcc(*'vp80')
                video_writer = cv2.VideoWriter(outputfilename, fourcc, fps, (line_object.get_image_width(), line_object.get_image_height()))

                img = cv2.imread("{}/{}/{}".format("output", ofname, list_of_images[0]))
                for _ in range(4 * fps):
                    video_writer.write(img)

                for image_path in list_of_images[1:-1]:
                    img = cv2.imread("{}/{}/{}".format("output", ofname, image_path))
                    video_writer.write(img)

                img = cv2.imread("{}/{}/{}".format("output", ofname, list_of_images[-1]))
                for _ in range(4 * fps):
                    video_writer.write(img)

                if kwargs.get("do_reverse"):
                    for image_path in reversed(list_of_images[1:-1]):
                        img = cv2.imread("{}/{}/{}".format("output", ofname, image_path))
                        video_writer.write(img)

                video_writer.release()

        if not kwargs.get("yes"):
            input("Render completed. Press ENTER to exit the script.")
