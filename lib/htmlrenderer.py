# I just need to throw this code elsewhere cuz I think it is going to be pretty big and messy when someone more professional gets to tinker with it.
def html_render(plot_object, table_string):
    title = plot_object.get_output_folder_name()
    iwidth = plot_object.get_image_width() // 4
    iheight = plot_object.get_image_height() // 4
    
    timeinterval = str(30 * 1000)
    
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

</script>""".format(timeinterval=timeinterval)

    page = """<html>
<head>
<title>Rendered plot of {title}</title>
<style>
{style}
</style>
</head>
<body>
{table}

<div class="overlay" id="overlay">
    <img id="overlayImage" src="" alt="">
    <div id="overlayText" class="overlay-text"></div>
</div>

{script}

</body>
</html>""".format(title=title, style=style, script=script, table=table_string)
    
    return page
