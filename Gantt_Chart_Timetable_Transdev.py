import streamlit as st
import pandas as pd
import plotly.express as px

# Make webpage
st.set_page_config(page_title="Busplan", layout="wide") # default settings of the webpage
st.title("Busplan Transdev") # title of the webpage

# the option to upload a dataframe in the webpage
st.subheader("Import data")
uploaded_file = st.file_uploader( # upload button
    "Upload an Excel file",
    type=["xlsx", "xls"] # it will only allow Excel files
)

if uploaded_file is not None: # you cannot run this unless a file has been uploaded
    timetable = pd.read_excel(uploaded_file) # turn the uploaded file into a pandas dataframe

    st.success(f"'{uploaded_file.name}' has been succesfully uploaded!")
    st.dataframe(timetable) # print the uploaded dataframe

    # timetable = pd.read_excel(r"C:\Users\Merel\OneDrive\Documenten\AA Fontys Toegepaste Wiskunde\Jaar 2\Periode 5\PJ5\Bus Planning.xlsx")

    # st.subheader("Timetable data") # a subheader for the dataframe
    # st.dataframe(timetable) # print the dataframe underneath the header

    # Vereiste kolommen? Met check?
    # Busnummer
    # Start 
    # Einde

    timetable["start time"] = pd.to_datetime(timetable["start time"]) # convert the departure times into datetimes
    timetable["end time"] = pd.to_datetime(timetable["end time"]) # convert the arrival times into datetimes

    bus_nummers = sorted(timetable["bus"].unique())

    # Plot Gantt chart planning
    gantt = px.timeline(
        timetable, # data used for Gantt chart planning
        x_start="start time", # starting value of the x axis
        x_end="end time", # x axis value limit
        y="bus", # y axis values -> bus numbers
        color="activity", # Gantt chart colored based on busactivity
        color_discrete_sequence=px.colors.qualitative.Plotly, # color palette
        title="Planning per bus number - Line 400 & line 401" # Title of Gantt chart
    )
    # Further lay-out of the Gantt chart
    gantt.update_layout(
        legend=dict(
            title="<b>Bus activity<b>", # legend title
            orientation='h', # legend goes horizontally
            yanchor='bottom', # placing the legend next to the title above the chart
            y=1.15,
            xanchor='center',
            x=0.7
        ),
        xaxis=dict(
            title="<b>Tijd</b>", # x axis title
            type="date", # x axis is over time (date)
            showgrid=True, # vertical lines to help tell time
            gridcolor="#E0E0E0", # color of the lines
            gridwidth=1, # width of the lines
            dtick=3600000, # x axis values per hour (in seconds)
            tickformat="%Hh", # only show whole hours
            showline=True, # line to seperate the time stamps from the chart
            linecolor="#cccccc" # color of that line
        ),
        yaxis=dict( # same thing for the y axis
        title="<b>Bus</b>",
        showgrid=True,
        gridcolor="#f3f3f3",
        gridwidth=1,
        tickmode='array',
        tickvals=bus_nummers, # to help seperate the bus numbers on the y axis values
        ticktext=[str(b) for b in bus_nummers],  # how the numbers will be printed
        autorange="reversed" # start with bus number 1 on the top
    )
    )

    # Thin white lines in between the bars for more clarity
    gantt.update_traces(marker=dict(line=dict(color="#ffffff", width=1)))

    # Put the bus numbers reversed on de y axis so that you start on the top with the first bus
    gantt.update_yaxes(autorange="reversed")

    st.plotly_chart(gantt, use_container_width=True) # Show Gantt chart
