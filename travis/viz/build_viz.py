# Import from our sibling directory
from travis import build_info

# Taken from great blog post by pygal folks:
# https://www.blog.pythonlibrary.org/2015/04/16/using-pygal-graphs-in-flask/
import pygal
import json
from urllib2 import urlopen  # python 2 syntax
# from urllib.request import urlopen # python 3 syntax


from flask import Flask
from pygal.style import DarkSolarizedStyle

app = Flask(__name__)

@app.route('/')
def get_build_info_times():
    """
    Render build times as provided by build_info
    """

    data = build_info.get_average_duration_org('edx')



    title = 'Average build duration for edX builds on public Travis instance.'

    x_series = [x['repo'] for x in data]
    y_series = [y['average duration'] for y in data]

    bar_chart = pygal.Bar(width=1200, height=600,
                          explicit_size=True, title=title, style=DarkSolarizedStyle,
                          x_label_rotation=45, pretty_print=True)

    bar_chart.x_labels = x_series

    bar_chart.add('Avg Build Duration', y_series)

    html = """
        <html>
             <head>
                  <title>%s</title>
             </head>
              <body>
                 %s
             </body>
        </html>
        """ % (title, bar_chart.render())
    return html

