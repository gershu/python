

import plotly.offline as pyo
import plotly.graph_objs as go


import pandas as pd

df=pd.read_csv('/Users/stefanhummel/Documents/GitHub/Plotly-Dashboards-with-Dash/Data/2018WinterOlympics.csv')


trace1=go.Bar(x=df['NOC'],
            y=df['Gold'],
            name='Gold',
            marker={'color':'#FFD700'})

trace2=go.Bar(  x=df['NOC'],
                y=df['Silver'],
                name='Silver',
                )

trace3=go.Bar(  x=df['NOC'],
                y=df['Bronze'],
                name='Bronze',
                marker={'color':'#CD7F32'})

data=[trace1,trace2,trace3]

layout=go.Layout(title='Olympics Medals',barmode='stack')

fig=go.Figure(data=data,layout=layout)
pyo.plot(fig)