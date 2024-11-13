# ComfyUI Grid Maker
So, you want to make yourself a fancy XY grid with images like in Automatic1111, but want to do it in ComfyUI? Find a XYZ grid too small for your liking? I've got you, buddy!

Introducing the ComfyUI Grid Maker - now with INFINITELY-SIZED supported grids (yes, MORE THAN Automatic's MEASELY THREE dimensions!)

## How to install?
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
    2. Write next string here: `@call .venv/Scripts/activate.bat`
    3. Write another string on a new line: `python xy_plot.py --autoreduce 10000 %*`.
    4. Save file as `run.bat`
6. Install your favorite font.
    1. Open your Windows Fonts folder (C:\Windows\Fonts)
    2. Copy the font you like (for example, Arial). **It must be in TrueType format.**
    3. Paste it into Grid Maker.
    4. Rename it to `font.ttf`

You have successfully installed Grid Maker

## How to use?
### Step 1: Create a Stencil.
1. Enter your ComfyUI and make a brand new workflow that you want to automate. **It must have EXACTLY one image output, EXACTLY one 'save image' node.**
2. Press 'Workflow' -> 'Export (API)'. If there is no such function, go to ComfyUI settings (cogwheel on the bottom-left of the page) and activate Dev Mode.
3. Save the file inside Grid Maker. You can give it any name, but I advice to stick to some kind of naming, for example: `stencil_sdxl.json`
4. Open the saved Stencil, and replace any values with Variables. What is a Variable? Variable is a piece of unique text, that can be automatically replaced. Look below for the example.
5. After all values has been replaced by Variables, save the JSON file. Your stencil is ready.

Here is an example of what you will find in a unmodified version of JSON, before you turn it into Stencil.
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

* `Image_Width` and `Image_Height` - you must set them to the output size of your generated picture. They are crucial for when generation of a grid takes place.
* `Variables` - this is your static, unchanging variables. The Grid Maker will replace every single instance of the variables with the value of the variable. Try to make sure they all are in double quotes, just in case. If you need to set a `\` symbol, you need to place four of them (example: `man \\\\(human\\\\)`)
* `Axises` - this is your dynamic, changing variables. The Grid Maker will replace every single instance of the variable in parameter `replace` with the every value you set in parameters `with`. Try to make sure they all are in double quotes, just in case.
* `WorkflowPath` - a path (relative or absolute) to your Stencil you made in Step 1
* `OutputFolderName` - when working, script will download a lot of files into a somewhat temprorary directory. This parameter controls the name of this directory. Advice: Always change it.

There is couple of variables that is actually hardcoded:

```
IMAGE_WIDTH  - Is replaced with the Image_Width value
IMAGE_HEIGHT  - same, but for height
OUTPUT_FOLDER_NAME  - is replaced with OutputFolderName value
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