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
    data = pd.read_excel(uploaded_file) # turn the uploaded file into a pandas dataframe

    st.success(f"'{uploaded_file.name}' has been succesfully uploaded!")
    st.dataframe(data) # print the uploaded dataframe

    valid_locations = ['ehvgar', 'ehvbst', 'ehvapt']

    df_busplanning_copy = data.copy()

    def check_column(df, columname, valid_values, nan_allowed=False):
        for index, row in df.iterrows(): # index allows you to find out in which "numbered" row a value is located 
            cel_value = row[columname]


            if pd.isna(cel_value): # is the cell empty? let's check if it's allowed to be empty
                if not nan_allowed:
                    print(f'Row {index} (Excel-row {index + 2}), column {columname}')
                continue
            
            if cel_value not in valid_values:
                print(f"Row {index} (Excel-row {index + 2}), column '{columname}': '{cel_value}' is not a valid value") # index + 2 omdat het een excelbestand is en dan zie je in welke rij in het excel bestand de foutieve waarde staat

    # function call - are all locations correct? are there any locations we don't recognize?
    check_column(df_busplanning_copy, 'start location', valid_locations)

    check_column(df_busplanning_copy, 'end location', valid_locations)

    valid_activies = ['material trip', 'service trip', 'idle', 'charging']

    # are there any activities we don't recognize??
    check_column(df_busplanning_copy, 'activity', valid_activies)

    valid_line_values = [400, 401]

    check_column(df_busplanning_copy, 'line', valid_line_values, nan_allowed= True)

    def check_line_by_idle_material(df):   # are the cells that are supposed to be empty, empty? 
        activities_without_line = ['idle', 'material trip']
        
        for index, row in df.iterrows():
            if row['activity'] in activities_without_line:
                if pd.notna(row['line']):   # if the 'line' column of this row actually contains a value (i.e. not an empty/NaN cell)
                    print(f"Row {index} (Excel-row {index + 2}): activity is '{row['activity']}' but 'line' is not empty (value: {row['line']})")

    check_line_by_idle_material(df_busplanning_copy)

    def check_charging_negative(df): # when the bus is charging, is the energy consumption negative? 
        for index, row in df.iterrows():
            if row['activity'] == 'charging':
                if row['energy consumption'] >= 0:
                    print(f"Row {index} (Excel-row {index + 2}): activity is 'charging' but energy consumption is {row['energy consumption']} (supposed to be negative)")

    check_charging_negative(df_busplanning_copy)

    # Convert time columns to actual datetime objects
    df_busplanning_copy['start time'] = pd.to_datetime(df_busplanning_copy['start time'], format='%H:%M:%S')
    df_busplanning_copy['end time'] = pd.to_datetime(df_busplanning_copy['end time'], format='%H:%M:%S')

    # midnight correction: if end time appears to be before start time,
    # the activity continues past midnight, so one day is added
    df_busplanning_copy.loc[
        df_busplanning_copy['end time'] < df_busplanning_copy['start time'], 'end time'
    ] += pd.Timedelta(days=1)


    # does every service trip have a line? 
    def check_service_trip_has_line(df):
        for index, row in df.iterrows():
            if row['activity'] == 'service trip' and pd.isna(row['line']):
                print(f"Row {index} (Excel-row {index + 2}): activity is 'service trip' but 'line' is empty")

    check_service_trip_has_line(df_busplanning_copy)

    # every activity exept for charging need to have a negative energy consumption 
    def check_positive_energy(df, activities):
        for index, row in df.iterrows():
            if row['activity'] in activities and row['energy consumption'] < 0:
                print(f"Row {index} (Excel-row {index + 2}): activity is '{row['activity']}' "
                    f"but energy consumption is {row['energy consumption']} (should be positive)")
    check_positive_energy(df_busplanning_copy, ['material trip', 'service trip'])

    # is idle everytime the same value? don't know if this is necessary  ??????????? but otherwise we could programm it that itl be 5/60 so we can have it per miniute

    def check_idle_consumption(df, expected_value=5.0):
        for index, row in df.iterrows():
            if row['activity'] == 'idle' and row['energy consumption'] != expected_value:
                print(f"Row {index} (Excel-row {index + 2}): activity is 'idle' but energy consumption "
                    f"is {row['energy consumption']} (expected {expected_value})")

    check_idle_consumption(df_busplanning_copy)


    # are there any exact the same rows ? (dubble rows)
    def check_duplicate_rows(df):
        duplicates = df[df.duplicated(keep=False)]
        
        if duplicates.empty:
            print("No duplicate rows found.")
        else:
            print(f"{len(duplicates)} duplicate row(s) found:")
            for index, row in duplicates.iterrows():
                print(f"  Row {index} (Excel-row {index + 2}): {row.to_dict()}")

    check_duplicate_rows(df_busplanning_copy)

    # if strat time is equal to end time, delete the whole row, print wich rows are deleted and the count
    def remove_start_equals_end(df):
        rows_to_remove = df[df['start time'] == df['end time']]
        print(f"{len(rows_to_remove)} row(s) removed where start time equals end time:")
        for index, row in rows_to_remove.iterrows():
            print(f"Excel-row {index + 2}")
        
        df_cleaned = df[df['start time'] != df['end time']].reset_index(drop=True)
        return df_cleaned

    df_busplanning_copy = remove_start_equals_end(df_busplanning_copy)


    # is the end location the same location where the bus starts the next trip 
    def check_location_continuity(df):
        for bus_id, group in df.groupby('bus', sort=False):
            group = group.reset_index(drop=True)
            for i in range(len(group) - 1):
                current_end = group.loc[i, 'end location']
                next_start = group.loc[i + 1, 'start location']
                
                if current_end != next_start:
                    print(f"Bus {bus_id}: row ends at '{current_end}' ({group.loc[i, 'end time']}) "
                        f"but next row starts at '{next_start}' ({group.loc[i + 1, 'start time']})")

    check_location_continuity(df_busplanning_copy)


    # de energy consumption van idle time in juiste hoeveelheid zetten
    idle_rows = df_busplanning_copy['activity'] == 'idle'

    duration_minutes = (
        df_busplanning_copy.loc[idle_rows, 'end time'] - df_busplanning_copy.loc[idle_rows, 'start time']
    ).dt.total_seconds() / 60

    berekende_energie = (df_busplanning_copy.loc[idle_rows, 'energy consumption'] / 60) * duration_minutes

    df_busplanning_copy.loc[idle_rows, 'energy consumption'] = berekende_energie


    data["start time"] = pd.to_datetime(data["start time"], format='%H:%M:%S') # convert the departure times into datetimes
    data["end time"] = pd.to_datetime(data["end time"], format='%H:%M:%S') # convert the arrival times into datetimes

    bus_numbers = sorted(data["bus"].unique()) # Edit the bus numbers variables to seperate the values when you plot them on the y axis of the gantt chart

    # Plot Gantt chart planning
    gantt = px.timeline(
        df_busplanning_copy, # data used for Gantt chart planning
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
        tickvals=bus_numbers, # to help seperate the bus numbers on the y axis values
        ticktext=[str(b) for b in bus_numbers],  # how the numbers will be printed
        autorange="reversed" # start with bus number 1 on the top
    )
    )

    # Thin white lines in between the bars for more clarity
    gantt.update_traces(marker=dict(line=dict(color="#ffffff", width=1)))

    # Put the bus numbers reversed on de y axis so that you start on the top with the first bus
    gantt.update_yaxes(autorange="reversed")

    st.plotly_chart(gantt, use_container_width=True) # Show Gantt chart
