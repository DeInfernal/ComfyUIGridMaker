# ComfyUI Grid Maker
So, you want to make yourself a fancy XY grid with images like in Automatic1111, but want to do it in ComfyUI? Find a XYZ grid too small for your liking? I've got you, buddy!

Introducing the ComfyUI Grid Maker - now with INFINITELY-SIZED supported grids (yes, MORE THAN Automatic's MEASELY THREE dimensions!)

## How to install?
### For Windows users
You don't need all this nonsense for Linux geeks. Just download latest release, unzip it and you are gucci!

I already put all the nessesary files like free font.ttf, and even a run.bat file inside. Even with an example workflow and plotfile, just for you! :)

So... Go for 'how to use' section.

### For Linux users
1. You need a Python 3. It doesn't really matter winch version, but I recommend using 3.10 or something like that.
2. Download the Grid Maker's Code. (press the green Code button, then Download Zip, then unpack in any suitable place)
3. Create a python virtual environment.
    1. In windows: Shift + press right click on empty space inside Grid Maker's folder.
    2. Select "Open Powershell Window Here"
    3. Enter next command: `python -m venv venv`
4. Install the requirements for Grid Maker (my ComfyUI API library)
    1. In windows: Shift + press right click on empty space inside Grid Maker's folder.
    2. Select "Open Powershell Window Here"
    3. Enter next command: `venv\Scripts\Activate.ps1`
    4. Enter next command: `pip install -r requirements.txt`
5. Create a runner file.
    1. Open a Notepad in Grid Maker folder.
    2. To use my script, you need for a runner to be inside a virtual environment. Write first string: `@call venv/Scripts/activate.bat`. (a path to your venv folder, followed by Scripts/activate.bat)
    3. Then use a virtual's environment Python to run the script. Write second string on a new line: `python xy_plot.py --autoreduce 10000 %*`. (to use my script, you need to specify flags and a path to plotfile in the end - for earlier you can look down, for latter, that is what %* is doing)
    4. Save file as `run.bat`
6. Install your favorite font.
    1. Open your Windows Fonts folder (C:\Windows\Fonts)
    2. Copy the font you like (for example, Arial). **It must be in TrueType format.**
    3. Paste it into Grid Maker.
    4. Rename it to `font.ttf`

You have successfully installed Grid Maker

### For MacOS users
Well, you can try using Linux users route, but I'm sure that you don't even need ComfyUI in the first place. Try Midjourney.

### For Android/iOS users
If you somehow manage to install Python on those devices and complete all the steps for Linux users... congratulations, you are already smarter than me, couldn't help you in any meaningful way >:D

## How to use?
### Step 1: Create a Stencil.
1. Enter your ComfyUI and make a brand new workflow that you want to automate. **It must have EXACTLY one image output, EXACTLY one 'save image' node.**
2. Press 'Workflow' -> 'Export (API)'. If there is no such function, go to ComfyUI settings (cogwheel on the bottom-left of the page) and activate Dev Mode.
3. Save the file inside Grid Maker. You can give it any name, but I advice to stick to some kind of naming, for example: `stencil_sdxl.json`
4. Open the saved Stencil, and replace any values with Variables. What is a Variable? Variable is a piece of unique text, that can be automatically replaced. Look below for the example.
5. After all values has been replaced by Variables, save the JSON file. Your stencil is ready.

Here is an example of what you will find in a unmodified version of JSON, before you turn it into Stencil. (NOTICE: if you do have an API version, you wouldn't have things like "size", or "pos", or "color". If you do, then you saved the workflow in normal mode, not an API-mode. Go back to step 2 and save it as API.)
```json
  "20": {
    "inputs": {
      "seed": 6,
      "steps": 24,
      "cfg": 2.0,
      "sampler_name": "euler_ancestral",
      "scheduler": "beta",
      "denoise": 1,
      "model": [
        "1",
        0
      ],
      "positive": [
        "19:11",
        0
      ],
      "negative": [
        "19:12",
        0
      ],
      "latent_image": [
        "4",
        0
      ]
    },
    "class_type": "KSampler",
    "_meta": {
      "title": "KSampler"
    }
```

Let's imagine that I want to have Script to automatically switch seeds and amount of steps for me. So, I could replace them with a UNIQUE STRINGS, that is not encountered anywhere in the file. Here is the example:
```json
  "20": {
    "inputs": {
      "seed": VAR_SEED,
      "steps": VAR_STEPS,
      "cfg": VAR_CFG,
      "sampler_name": "euler_ancestral",
      "scheduler": "beta",
      "denoise": 1,
      "model": [
        "1",
        0
      ],
      "positive": [
        "19:11",
        0
      ],
      "negative": [
        "19:12",
        0
      ],
      "latent_image": [
        "4",
        0
      ]
    },
    "class_type": "KSampler",
    "_meta": {
      "title": "KSampler"
    }
```

Notice, that `VAR_SEED` or `VAR_STEPS` is encounered EXACTLY ONCE in whole file, making it completely unique. Also notice, that my naming doesn't create sub-containing names, like `VAR_SEED` and `VAR_SEEDED_STEPS` (both have `VAR_SEED` in them).

How we substitute Variables? We create a PlotFile.

### Step 2: Create a Plotfile
First, create a new file (name it anyhow you want, I suggest naming like `plotfile_something.yaml`), and fill it with next template.

*Notice: It must be [in YAML-notation](https://en.wikipedia.org/wiki/YAML).*

```yaml
Image_Width: 1280
Image_Height: 1024
Variables:
  VAR_SEED: "24"
  VAR_CFG: "3.0"
Axises:
  - replace: "VAR_SOMETHING"
    with:
      - "1.0"
      - "1.1"
  ...
WorkflowPath: "workflow_chromaxl_api_friendly_basic.json"
OutputFolderName: "ExampleNum0001"
```

Now, fill it up as you need. I will explain every single setting.

* `Image_Width` and `Image_Height` - you must set them to the **output size of your generated picture**. They are crucial for when generation of a grid takes place.
* `Variables` - this is your static, unchanging variables. The Grid Maker will replace every single instance of the variables with the value of the variable. Try to make sure they all are in double quotes, just in case. If you need to set a `\` symbol, you need to place four of them (example: `man \\\\(human\\\\)`). Technically you can omit this parameter if you are never to have Variables, but I doubt it.
* `Axises` - this is your dynamic, changing variables. The Grid Maker will replace every single instance of the variable in parameter `replace` with the every value you set in parameters `with`. Try to make sure they all are in double quotes, just in case. The images will render in order from the first axis (top one) to the last one, so it first will fill the X axis of 1st XY plot, then Y axis of XY plot, then X axis of 2nd XY plot (shifted to X) and so on. You can actually add a parameter called `order`, with a numeric value (example: `order: 999`), and it will shift the order it will generate - useful to shift the order of checkpoints or loras to speed up generative process. By default, 1st axis have order of 0, 2nd axis of 1, 3rd of 2, etc...
* `WorkflowPath` - a path (relative or absolute) to your Stencil you made in Step 1. Without this setting, script won't know what workflow to use to generate anything.
* `OutputFolderName` - when working, script will download a lot of files into a somewhat temprorary directory. This parameter controls the name of this directory. Advice: Always change it. It is, well, optional, and if you miss it, it will download everything into a "GENERIC" folder.
* `OutputFileSuffix` - an extremely optional setting. If set, will save your finished file as `OutputFolderName + OutputFileSuffix.png` instead of `OutputFolderName.png`.

There is couple of variables that is actually hardcoded:

```
IMAGE_WIDTH  - Is replaced with the Image_Width value
IMAGE_HEIGHT  - same, but for height

IMAGE_[MODIFIER]_[SIDE]

where [MODIFIER]
* QUARTER
* HALF
* ONEANDATHIRDOFHALVED
* ONEANDAHALFOFHALVED
* ONEANDTWOTHIRDSOFHALVED
* ONEANDATHIRD
* ONEANDAHALF
* ONEANDTWOTHIRDS
* DOUBLE
* QUAD

and [SIDE]
* WIDTH
* HEIGHT

will result in an integer value of this side, multiplied by 0.25, 0.5, 0.66, 0.75, 0.83, 1.33, 1.5, 1.66, 2, or 4 respectively
-- NOTICE: The Image_Height and Image_Width in plotfile still must be an output size of picture, regardless of values of those modified variables.

OUTPUT_FOLDER_NAME  - is replaced with OutputFolderName value
OUTPUT_FILE_SUFFIX  - is replaced with OutputFileSuffix value
```

You can make any amount of Axises as you need. I recommend to stay at 3 to 4 Axises, unless you really want to crank up the heat.

Notice: When script replaces names of variables with actual values, it first replaces everything from Variables section, and then it replaces everything from Axises section. It allows you a complex, but interesting chains to form. Example:

```yaml
Image_Width: 1280
Image_Height: 1024
Variables:
  VAR_SEED: "24"
  VAR_CFG: "3.0"
  VAR_PROMPT: "blender, (room:VAR_ROOMNESS), 3d, VAR_SPECIES"
Axises:
  - replace: "VAR_ROOMNESS"
    with:
      - "1.0"
      - "1.1"
      - "1.2"
  - replace: "VAR_SPECIES"
    with:
      - "cat"
      - "dog"
      - "bird"
WorkflowPath: "workflow_chromaxl_api_friendly_basic.json"
OutputFolderName: "ExampleNum0001"
```

Because VAR_PROMPT is a Variable, it gets replaced for `blender, (room:VAR_ROOMNESS), 3d, VAR_SPECIES` first. And after, `VAR_ROOMNESS` replaced by `1.0` value, and `VAR_SPECIES` replaced by `cat` value.

The example makes a XY (2 dimension) plot, because there is 2 axises. X (the width) is VAR_ROOMNESS, and Y (height) is VAR_SPECIES.

### Step 3: Activate plot building!
Just drag your PlotFile onto `run.bat` you created while installing the Grid Maker.

Your result will wait for you in `OUTPUT` folder.


## Command-line flags
* `--comfyui_ip` - specifies a either web-address or ip-address of your comfyui. By default it is 127.0.0.1, meaning, the script thinks ComfyUI runs on your local computer.
* `--comfyui_port` - specifies a port of your comfyui. By default it is 8188, meaning, the script thinks ComfyUI never changed it's local port.
* `--resize_ratio` - if specified, also specify a floating-point number afterwards (example: `--resize_ratio 0.25`). This flag will forcibly resize the final XY-plot down to a specified ratio, making the file smaller, and therefore, more prone to be opened when the amount of Axises is big or when RAM is not high enough.
* `--autoreduce` - it works like resize_ratio, but instead, takes an integer number (example: `--autoreduce 10000`). This flag will check at the size of final XY-plot, and if it is larger than your specified number (for example, 12000 by 8000 pixels), the whole image will be resized to be at most 10000 pixels big (therefore automatically reducing XY plot size to 10000 by 6666).
* `--flip_last_axis` - Nice flag. Let's imagine that you generated any odd-numbered Axises. By default, they will stack horizontally, making it difficult to read, especially if your plots are wide, instead of tall. This flag will make sure that your last, final axis is stacked VERTCALLY instead of HORIZONTALLY. Try it out!
* `--autoflip_last_axis` - same as --flip_last_axis, but will automatically flip last axis for you if it is going to result in more squar-ish image (so, better for autoreduce!). This flag will overpower any presence of your `--flip_last_axis` flag. No need to use them both.
* `--hash_filenames` - in case something goes wrong with the naming scheme of the generator, you can use hashed filenames. Mostly useful if you use exactly only HTML tables, too.
* `--skip_mass_generation` - a very specific flag - if set, the program will skip the final XY-plot generation (so it will only make images that composes the plot, but not the plot itself).
* `--make_html_table` - in addition (or, if --skip_mass_generation is supplied, standalone) to graphical table, make an interactive HTML page where every single picture could be clicked, enlarged, etc.
* `--yes` - when generation is finished, the script will wait till you press 'enter' to finish it. Supply it with '--yes' flag, and it will not ask for any key, but shut down when it finishes.
* `--ignore_non_replacements` - another specific flag. If NOT set, then at the stage of replacing dynamic variables with values (found in Axises), if after replacing the variable, nothing has changed in the workflow, the program will halt with error, possibly notifying you that what you about to generate will look the same as your previous generations (since there was nothing to change in the first place anywhere). If you are somehow OKAY with that, and asknowledge that there is a points in script where nothing will change - you must set this flag, so program will not halt at those stages.


## Personal recommendations
1. Use a lot of variables, but don't forget to comment them out when you are testing them.
    ```yaml
    Image_Width: 1280
    Image_Height: 1024
    Variables:
        VAR_CHECKPOINT: "baseline_xl/chromaxlMix_v331Mango"
        # VAR_SEED: "42"
        # VAR_STEPS: "24"
        VAR_CFG: "2.0"
        VAR_PROMPT: "cat, VAR_VIEW, detailed fur, detailed, fur, cute, happy, VAR_BACKGROUND, VAR_STYLE"
        VAR_BACKGROUND: "simple background, pool"
        VAR_STYLE: "masterpiece, best quality"
        VAR_NEGATIVE: "worst quality, bad quality"
    Axises:
        - replace: "VAR_STEPS"
          with:
              - "8"
              - "12"
              - "24"
        - replace: "VAR_SEED"
          with:
              - "6"
              - "7"
              - "42"
              - "420"
              - "666"
              - "777"
              - "4242"
              - "424242"
              - "666666"
              - "696969"
              - "7777777"
        - replace: "VAR_VIEW"
          with:
              - "front view"
              - "side view"
              - "rear view"
    WorkflowPath: "workflow_chromaxl_api_friendly_basic.json"
    OutputFolderName: "Illust0001"
    ```
    (because VAR_BACKGROUND and VAR_STYLE is lower than VAR_PROMPT, they get to be replaced later, therefore making the chain of replacements within Variables themselves)
2. If you have a need to replace multiple values at the same time - you can! Just be sure you notate all of them at the same time.
    ```yaml
    Image_Width: 1024
    Image_Height: 1280
    Variables:
        VAR_CHECKPOINT: "baseline_xl/ponyDiffusionV6"
        # VAR_SEED: "42"
        # VAR_STEPS: "24"
        VAR_CFG: "2.0"
        VAR_PROMPT: "cat, VAR_VIEW, detailed fur, detailed, fur, cute, happy"
        VAR_BACKGROUND: "simple background, pool"
        VAR_STYLE: "score_9, score_8_up, score_7_up, score_6_up, score_5_up, score_4_up"
        VAR_NEGATIVE: "worst quality, bad quality"
    Axises:
        - replace: "VAR_STEPS"
          with:
              - "8"
              - "12"
              - "24"
        - replace: ["VAR_SEED", "VAR_VIEW"]
          with:
              - ["6", "side view"]
              - ["7", "side view"]
              - ["42", "rear view"]
              - ["420", "front view"]
    WorkflowPath: "workflow_chromaxl_api_friendly_basic.json"
    OutputFolderName: "Illust0001"
    ```
    (this will replace VAR_SEED and VAR_VIEW at the same time with a specific values, in case you need such specificality)
