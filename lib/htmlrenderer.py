# I just need to throw this code elsewhere cuz I think it is going to be pretty big and messy when someone more professional gets to tinker with it.
def html_render(plot_object, table_string):
    title = plot_object.get_output_folder_name()
    style = """
img {
    width: 100%;
    height: 100%;
}
img:hover {
    width: 500%;
    height: 500%;
}
td {
    text-align: center;
}
table {
    border:1px solid gray;
}  
    """
    return """<html>
<head>
<title>Rendered plot of {title}</title>
<style>
{style}
</style>
</head>
<body>
{table}
</body>
</html>""".format(title=title, style=style, table=table_string)
