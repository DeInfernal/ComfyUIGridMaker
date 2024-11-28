# I just need to throw this code elsewhere cuz I think it is going to be pretty big and messy when someone more professional gets to tinker with it.
def html_render(plot_object, table_string):
    axislist = plot_object.axises
    title = plot_object.get_output_folder_name()
    iwidth = plot_object.get_image_width() // 4
    iheight = plot_object.get_image_height() // 4
    
    # 30 secs if items are 1000 or lower
    # 180 secs if items are higher than 10000
    count_of_generated_objects = 1
    for axis in axislist:
        count_of_generated_objects *= axis.get_object_count()
    seconds_to_wait_on_reloads = int(30 + min(max(0, count_of_generated_objects-1000), 9000)/9000 * 150)
    timeinterval = str(seconds_to_wait_on_reloads * 1000)
    
    # Turn variables into better readable variants.
    all_existing_variables_and_their_list_values = dict()
    for axis in axislist:
        variablename = axis.get_variable_name()
        if not isinstance(variablename, str):
            all_objects = axis.get_objects()
            for subvariablename in enumerate(variablename):
                all_existing_variables_and_their_list_values.setdefault(subvariablename[1], list())
                for objectz in all_objects:
                    if objectz[subvariablename[0]] not in all_existing_variables_and_their_list_values[subvariablename[1]]:
                        all_existing_variables_and_their_list_values[subvariablename[1]].append(objectz[subvariablename[0]])
        else:
            all_existing_variables_and_their_list_values.setdefault(variablename, axis.get_objects())
    all_existing_variables_and_their_list_values_kv = sorted(all_existing_variables_and_their_list_values.items())

    # Now assemble the filter item
    checkbox_filter = "<div>\n"
    checkbox_filter += "<h3>Image filter:</h3>\n"
    checkbox_filter += "<i>Notice: Image filtering in beta-test mode, therefore, there is a lot of things that can be somewhat broken (like, if you have complex list variables). Otherwise, enjoy.</i><br>\n"
    checkbox_filter += "<table>\n"
    
    checkbox_filter += "<tr>\n"
    for variablename in all_existing_variables_and_their_list_values_kv:
        checkbox_filter += "<td><h4>{}</h4></td>".format(variablename[0])
    checkbox_filter += "</tr>\n"

    checkbox_filter += "<tr>\n"
    for variablename in all_existing_variables_and_their_list_values_kv:
        checkbox_filter += "<td>"
        for objectz in variablename[1]:
            checkbox_filter += "<label><input type=\"checkbox\" class=\"filter\" data-filter-type=\"{}\" value=\"{}\" checked>{}</label><br>".format(variablename[0].lower(), objectz, objectz)
        checkbox_filter += "</td>"
    checkbox_filter += "</tr>\n"

    checkbox_filter += "</table>\n"
    checkbox_filter += "</div>"
    
    
    style = """
body {{
    font-family: Arial, sans-serif;
    background-color: #ffc;
    margin: 0;
    padding: 20px;
}}
img.plot_img {{
    max-width: {width}px;
    max-height: {height}px;
    transition: transform 0.3s ease, z-index 0s linear 0.3s;
    cursor: pointer;
    position: relative;
}}
img.plot_img:hover {{
    transform: scale(2);
    z-index: 10;
}}
td {{
    padding: 1px;
    text-align: center;
    position: relative;
}}
table {{
    border-collapse: collapse;
    margin: 10px 0;
}}

.hidden {{
    display: none;
}}

.overlay {{
    display: none;    /* Hidden by default */
    position: fixed;  /* Stay in place */
    top: 0;
    left: 0;
    width: 100%;  /* Full width of screen */
    height: 100%; /* Full height of screen */
    background-color: rgba(0, 0, 0, 0.8);  /* Black background with some opacity */
    justify-content: center;  /* Center the contents */
    align-items: center;      /* Center the contents */
    z-index: 1000;  /* Sit on top of everything */
}}
.overlay img {{
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translateX(-50%) translateY(-50%);
    max-width: 90%;   /* Either full size of image or 90pct of screen, winch is higher */
    max-height: 80%;  /* Either full size of image or 80pct of screen, winch is higher */
}}
.overlay-text {{
    position: absolute;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    color: white;
    padding: 10px;
}}

tr.plot_depth_1, tr.plot_depth_2 {{
    background-color: #ff8000;
    font-size: 12pt;
}}
tr.plot_depth_3, tr.plot_depth_4 {{
    background-color: #ff9020;
    font-size: 16pt;
}}
tr.plot_depth_5, tr.plot_depth_6 {{
    background-color: #ffa040;
    font-size: 20pt;
}}
tr.plot_depth_7, tr.plot_depth_8 {{
    background-color: #ffb060;
    font-size: 24pt;
}}
tr.plot_depth_9, tr.plot_depth_10 {{
    background-color: #ffc080;
    font-size: 28pt;
}}
    """.format(width=iwidth, height=iheight)

    filterscript = ""
    for kv in all_existing_variables_and_their_list_values_kv:
        filterscript += "const selected{} = Array.from(checkboxes).filter(checkbox => checkbox.checked && checkbox.dataset.filterType === '{}').map(checkbox => checkbox.value);\n".format(kv[0].lower(), kv[0].lower())
    filterscript += "\n"
    filterscript += "images.forEach(image => {\n"
    for kv in all_existing_variables_and_their_list_values_kv:
        filterscript += "const image{} = image.getAttribute('data-{}');\n".format(kv[0].lower(), kv[0].lower())
    
    list_filterscript = list()
    for kv in all_existing_variables_and_their_list_values_kv:
        list_filterscript.append("selected{}.includes(image{})".format(kv[0].lower(), kv[0].lower()))

    filterscript += "if ("
    filterscript += " && ".join(list_filterscript)
    filterscript += ") {\n"
    filterscript += "image.classList.remove('hidden')\n"
    filterscript += "} else {\n"
    filterscript += "image.classList.add('hidden')\n"
    filterscript += "}\n"
    filterscript += "});"

    script = """
<script>
    // Function to handle image click and display overlay
    const images = document.querySelectorAll('img');
    const overlay = document.getElementById('overlay');
    const overlayImage = document.getElementById('overlayImage');
    const overlayText = document.getElementById('overlayText');

    images.forEach(img => {{
        img.addEventListener('click', () => {{
            overlayImage.src = img.src;
            overlayText.innerText = img.getAttribute('data-caption');
            overlay.style.display = 'block';
        }});
    }});

    // Close the overlay when clicking outside the image
    overlay.addEventListener('click', () => {{
        overlay.style.display = 'none';
    }});
    
    function checkImageLoaded(imgobj, intervalId) {{
        const imageCheck = new Image();
        imageCheck.src = imgobj.src + '?' + new Date().getTime();
        imageCheck.onload = () => {{
            imgobj.src = imageCheck.src;
            clearInterval(intervalId);
        }};
    }}
    
    const imageCells = document.querySelectorAll('td img');
    imageCells.forEach((img) => {{
        // Create a new image object to check if it loads successfully
        const imageCheck = new Image();
        imageCheck.src = img.src;

        imageCheck.onerror = () => {{
            const imgIntervalId = setInterval(() => {{
                checkImageLoaded(img, imgIntervalId);
            }}, {timeinterval});
        }};
    }});
    
    const checkboxes = document.querySelectorAll('.filter');
    const filteredimages = document.querySelectorAll('.plot-img');
    function filterImages() {{
            {filterscript}
        }}
        
    checkboxes.forEach(checkbox => {{
        checkbox.addEventListener('change', filterImages);
    }});
    

</script>""".format(filterscript=filterscript, timeinterval=timeinterval)

    page = """<html>
<head>
<title>Rendered plot of {title}</title>
<style>
{style}
</style>
</head>
<body>
<h1>Rendered XY plot of {title} folder</h1>
<div><i>Notice: If you have plots with more than 4000 images, you WILL need a beefy RAM.</i></div>
{checkbox_filter}
{table}

<div class="overlay" id="overlay">
    <img id="overlayImage" src="" alt="">
    <div id="overlayText" class="overlay-text"></div>
</div>

{script}

</body>
</html>""".format(checkbox_filter=checkbox_filter, title=title, style=style, script=script, table=table_string)
    
    return page
