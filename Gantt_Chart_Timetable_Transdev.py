import streamlit as st
import pandas as pd
import plotly.express as px

# Make webpage
st.set_page_config(page_title="Busplan", layout="wide")  # default settings of the webpage
st.title("Busplan Transdev")  # title of the webpage

# --- Fixed values used by the checks ---
required_columns = ['start location', 'end location', 'start time', 'end time', 'activity', 'line', 'energy consumption', 'bus']
valid_locations = ['ehvgar', 'ehvbst', 'ehvapt']
valid_activies = ['material trip', 'service trip', 'idle', 'charging']
valid_line_values = [400, 401]


# --- Function definitions ---

def check_required_columns(df, required_columns):
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        st.write(f"Missing column(s) in the uploaded file: {missing_columns}")
    else:
        st.write("All required columns are present.")
    return missing_columns


def check_column(df, columname, valid_values, nan_allowed=False):
    for index, row in df.iterrows():  # index allows you to find out in which "numbered" row a value is located
        cel_value = row[columname]

        if pd.isna(cel_value):  # is the cell empty? let's check if it's allowed to be empty
            if not nan_allowed:
                st.write(f'Row {index} (Excel-row {index + 2}), column {columname}')
            continue

        if cel_value not in valid_values:
            st.write(f"Row {index} (Excel-row {index + 2}), column '{columname}': '{cel_value}' is not a valid value")


def check_line_by_idle_material(df):  # are the cells that are supposed to be empty, empty?
    activities_without_line = ['idle', 'material trip']

    for index, row in df.iterrows():
        if row['activity'] in activities_without_line:
            if pd.notna(row['line']):  # if the 'line' column of this row actually contains a value (i.e. not an empty/NaN cell)
                st.write(f"Row {index} (Excel-row {index + 2}): activity is '{row['activity']}' but 'line' is not empty (value: {row['line']})")


def check_charging_negative(df):  # when the bus is charging, is the energy consumption negative?
    for index, row in df.iterrows():
        if row['activity'] == 'charging':
            if row['energy consumption'] >= 0:
                st.write(f"Row {index} (Excel-row {index + 2}): activity is 'charging' but energy consumption is {row['energy consumption']} (supposed to be negative)")


def check_service_trip_has_line(df):  # does every service trip have a line?
    for index, row in df.iterrows():
        if row['activity'] == 'service trip' and pd.isna(row['line']):
            st.write(f"Row {index} (Excel-row {index + 2}): activity is 'service trip' but 'line' is empty")


def check_positive_energy(df, activities):  # every activity except for charging needs to have a positive energy consumption
    for index, row in df.iterrows():
        if row['activity'] in activities and row['energy consumption'] < 0:
            st.write(f"Row {index} (Excel-row {index + 2}): activity is '{row['activity']}' "
                     f"but energy consumption is {row['energy consumption']} (should be positive)")


def check_idle_consumption(df, expected_value=5.0):
    for index, row in df.iterrows():
        if row['activity'] == 'idle' and row['energy consumption'] != expected_value:
            st.write(f"Row {index} (Excel-row {index + 2}): activity is 'idle' but energy consumption "
                     f"is {row['energy consumption']} (expected {expected_value})")


def check_duplicate_rows(df):  # are there any exact the same rows? (double rows)
    duplicates = df[df.duplicated(keep=False)]

    if duplicates.empty:
        st.write("No duplicate rows found.")
    else:
        st.write(f"{len(duplicates)} duplicate row(s) found:")
        for index, row in duplicates.iterrows():
            st.write(f"Row {index} (Excel-row {index + 2}): {row.to_dict()}")


def remove_start_equals_end(df):  # if start time equals end time, delete the whole row, print which rows are deleted and the count
    rows_to_remove = df[df['start time'] == df['end time']]
    st.write(f"{len(rows_to_remove)} row(s) removed where start time equals end time.")

    df_cleaned = df[df['start time'] != df['end time']].reset_index(drop=True)
    return df_cleaned


def check_location_continuity(df):  # is the end location the same location where the bus starts the next trip
    for bus_id, group in df.groupby('bus', sort=False):
        group = group.reset_index(drop=True)
        for i in range(len(group) - 1):
            current_end = group.loc[i, 'end location']
            next_start = group.loc[i + 1, 'start location']

            if current_end != next_start:
                st.write(f"Bus {bus_id}: row ends at '{current_end}' ({group.loc[i, 'end time']}) "
                         f"but next row starts at '{next_start}' ({group.loc[i + 1, 'start time']})")


# --- The webpage itself ---

st.subheader("Import data")
uploaded_file = st.file_uploader(  # upload button
    "Upload an Excel file",
    type=["xlsx", "xls"]  # it will only allow Excel files
)

if uploaded_file is not None:  # you cannot run this unless a file has been uploaded
    data = pd.read_excel(uploaded_file)  # turn the uploaded file into a pandas dataframe

    st.success(f"'{uploaded_file.name}' has been succesfully uploaded!")

    # make a copy right at the start - everything from here on works on this copy
    df_busplanning_copy = data.copy()

    st.subheader("Data quality checks")

    missing_columns = check_required_columns(df_busplanning_copy, required_columns)

    if not missing_columns:

        check_column(df_busplanning_copy, 'start location', valid_locations)
        check_column(df_busplanning_copy, 'end location', valid_locations)
        check_column(df_busplanning_copy, 'activity', valid_activies)
        check_column(df_busplanning_copy, 'line', valid_line_values, nan_allowed=True)

        check_line_by_idle_material(df_busplanning_copy)
        check_charging_negative(df_busplanning_copy)

        # Convert time columns to actual datetime objects
        df_busplanning_copy['start time'] = pd.to_datetime(df_busplanning_copy['start time'], format='%H:%M:%S')
        df_busplanning_copy['end time'] = pd.to_datetime(df_busplanning_copy['end time'], format='%H:%M:%S')

        # midnight correction: if end time appears to be before start time,
        # the activity continues past midnight, so one day is added
        df_busplanning_copy.loc[
            df_busplanning_copy['end time'] < df_busplanning_copy['start time'], 'end time'
        ] += pd.Timedelta(days=1)

        check_service_trip_has_line(df_busplanning_copy)
        check_positive_energy(df_busplanning_copy, ['material trip', 'service trip'])
        check_idle_consumption(df_busplanning_copy)
        check_duplicate_rows(df_busplanning_copy)

        df_busplanning_copy = remove_start_equals_end(df_busplanning_copy)

        check_location_continuity(df_busplanning_copy)

        # de energy consumption van idle time in juiste hoeveelheid zetten
        idle_rows = df_busplanning_copy['activity'] == 'idle'

        duration_minutes = (
            df_busplanning_copy.loc[idle_rows, 'end time'] - df_busplanning_copy.loc[idle_rows, 'start time']
        ).dt.total_seconds() / 60

        berekende_energie = (df_busplanning_copy.loc[idle_rows, 'energy consumption'] / 60) * duration_minutes

        df_busplanning_copy.loc[idle_rows, 'energy consumption'] = berekende_energie

        st.subheader("Imported data")
        st.dataframe(data)  # show the raw, uploaded dataframe

                # --- Gantt chart, built on the checked and cleaned data ---
        bus_numbers = sorted(df_busplanning_copy["bus"].unique())

        # pre-formatted hour:minute strings, used for the hover text (independent of the axis tickformat)
        df_busplanning_copy['start_time_str'] = df_busplanning_copy['start time'].dt.strftime('%H:%M') + 'h'
        df_busplanning_copy['end_time_str'] = df_busplanning_copy['end time'].dt.strftime('%H:%M') + 'h'

        st.subheader("Gantt chart")

        gantt = px.timeline(
            df_busplanning_copy,  # data used for Gantt chart planning
            x_start="start time",  # starting value of the x axis
            x_end="end time",  # x axis value limit
            y="bus",  # y axis values -> bus numbers
            color="activity",  # Gantt chart colored based on busactivity
            color_discrete_sequence=px.colors.qualitative.Plotly,  # color palette
            title="Planning per bus number - Line 400 & line 401",  # Title of Gantt chart
            custom_data=['start_time_str', 'end_time_str']  # carried through to the hover template below
        )

        # custom hover text: "field = value" with hour:minute times, independent of the axis tickformat
        gantt.update_traces(
            hovertemplate=(
                "activity = %{fullData.name}<br>"
                "start time = %{customdata[0]}<br>"
                "end time = %{customdata[1]}<br>"
                "bus = %{y}"
                "<extra></extra>"
            )
        )
        
        # Further lay-out of the Gantt chart
        gantt.update_layout(
            legend=dict(
                title="<b>Bus activity<b>",  # legend title
                orientation='h',  # legend goes horizontally
                yanchor='bottom',  # placing the legend next to the title above the chart
                y=1.15,
                xanchor='center',
                x=0.7
            ),
            xaxis=dict(
                title="<b>Tijd</b>",  # x axis title
                type="date",  # x axis is over time (date)
                showgrid=True,  # vertical lines to help tell time
                gridcolor="#E0E0E0",  # color of the lines
                gridwidth=1,  # width of the lines
                dtick=3600000,  # x axis values per hour (in seconds)
                tickformat="%Hh",  # only show whole hours
                showline=True,  # line to seperate the time stamps from the chart
                linecolor="#cccccc"  # color of that line
            ),
            yaxis=dict(  # same thing for the y axis
                title="<b>Bus</b>",
                showgrid=True,
                gridcolor="#f3f3f3",
                gridwidth=1,
                tickmode='array',
                tickvals=bus_numbers,  # to help seperate the bus numbers on the y axis values
                ticktext=[str(b) for b in bus_numbers],  # how the numbers will be printed
                autorange="reversed"  # start with bus number 1 on the top
            )
        )

        # Thin white lines in between the bars for more clarity
        gantt.update_traces(marker=dict(line=dict(color="#ffffff", width=1)))

        # Put the bus numbers reversed on de y axis so that you start on the top with the first bus
        gantt.update_yaxes(autorange="reversed")

        st.plotly_chart(gantt, use_container_width=True)  # Show Gantt chart

    else:
        st.error(f"Cannot proceed: required columns are missing from the uploaded file: {missing_columns}")
        st.subheader("Imported data")
        st.dataframe(data)  # show the raw, uploaded dataframe, so the user can inspect what went wrong

     # Pie chart with the ratios of the bus activity
    st.subheader("KPI GERELATEERD --> DUS KPI OF LETTERLIJK PIE CHART RATIOS?")
    piechart_sort_trip = px.pie(data, names="activity", title="Ratio bus activities", color_discrete_sequence=px.colors.qualitative.Plotly)
    
    piechart_sort_trip.update_layout(
        title_x=0.5,
        legend_title_text="<b>Different kind of trips</b>" # gives the pie chart a centered title
    )
    piechart_sort_trip.update_traces(
        textposition="inside",
        textfont=dict(color="white") # put the text in the pie parts with a white color
    )

    col_left, col_mid, col_right = st.columns([1, 2, 1])
    with col_mid:
        st.plotly_chart(piechart_sort_trip, use_container_width=True) # center the pie chart