""" import dash, pandas, and psycopg2 """
import os
import psycopg2
import dash
import dash_ag_grid as dag
from dash import html, dcc, Input, Output, State, no_update, callback_context
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go


# Initialize Dash app
app = dash.Dash(__name__)
server = app.server

# Initialize an empty DataFrame
df = pd.DataFrame()
deleted_row_ids_store = dcc.Store(id='deleted-row-ids-store', storage_type='memory', data=[])


def connect_to_db():
    conn_params = {
        'host': os.getenv('HOST'),
        'database': os.getenv('DATABASE'),
        'user': os.getenv('USER'),
        'password': os.getenv('PASSWORD'),
        'port': os.getenv('DB_PORT'),
    }

    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()
    return conn, cur

# Modify the fetch_data_from_db function to fetch data from the PostgreSQL table
def fetch_data_from_db():
    """Function to fetch data from PostgreSQL table"""
    global df  # Declare df as global

    conn, cur = connect_to_db()
    try:
        # Fetch data from the CallTracker_table
        cur.execute("SELECT * FROM calltracker_table;")
        data = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        df = pd.DataFrame(data, columns=columns)
        return df.to_dict("records")

    except psycopg2.Error as e:
        print("Error fetching data from database:", e)
        return []

    finally:
        # Close the cursor and the connection
        cur.close()
        conn.close()

fetch_data_from_db()

# Function to fetch existing submission IDs from the PostgreSQL table
def fetch_existing_submission_ids_from_db():
    """Function to fetch existing submission IDs from PostgreSQL table"""

    conn, cur = connect_to_db()
    try:
        # Fetch existing submission IDs
        cur.execute("SELECT submission_id FROM calltracker_table;")
        existing_ids = cur.fetchall()
        existing_submission_ids = [id[0] for id in existing_ids]
        return existing_submission_ids

    except psycopg2.Error as e:
        print("Error fetching existing submission IDs from database:", e)
        return []

    finally:
        # Close the cursor and the connection
        cur.close()
        conn.close()

# Fetch existing submission IDs from the PostgreSQL table
existing_submission_ids = fetch_existing_submission_ids_from_db()

graph = dcc.Graph(id='bar-line-chart', figure={})

# Filter out null values from 'Day' column
available_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
call_times = ["12:00 PM", "12:30 PM", "1:00 PM", "1:30 PM",
    "2:00 PM", "2:30 PM", "3:00 PM", "3:30 PM",
    "4:00 PM", "4:30 PM", "5:00 PM", "5:30 PM"]
pick_up = ["Yes", "No"]


columnDefs = [
    {"field": "day", "headerName": "Day",  "checkboxSelection": True},
    {"field": "call_time", "headerName": "Call time"},
    {"field": "pick_up", "headerName": "Pick up"},
    {"field": "submit_date", "headerName": "Submit date"},
    {"field": "good_time_for_3min_talk", "headerName": "Good time to talk"},
    {"field": "job", "headerName": "Job status"},
    {"field": "submission_id", "headerName": "Submission ID"},
]

# Define layout
app.layout = html.Div([
    dcc.Dropdown(
        id='day-dropdown',
        options=[{'label': day, 'value': day} for day in available_days],
        value='Sunday',
        clearable=False,
        className="info-text"
    ),
    html.Br(),
    html.Br(),
    html.Div([
        graph
    ], id="chart-breakdown"),
    html.Br(),
    html.Br(),
    html.H4(["Please fill out the new row values, ",
    html.Span("save changes", className="highlighted-text"),
    " when satisfied with row additions and deletions"
], className="info-text"),
    html.Div([
        dcc.Dropdown(
            id='col-day',
            options=[{'label': d, 'value': d} for d in available_days],
            value='DayOfCall',
            clearable=False,
            className='drop-columns info-text',
            placeholder='Select the day',
        ),
        dcc.Dropdown(
            id='col-ct',
            options=[{'label': ct, 'value': ct} for ct in call_times],
            value='',
            clearable=False,
            className='drop-columns info-text',
            placeholder='Select a time of call',
        ),
        dcc.Dropdown(
            id='col-pu',
            options=[{'label': pu, 'value': pu} for pu in pick_up],
            value='YesOrNo',
            clearable=False,
            className='drop-columns info-text',
            placeholder='Did they pick up',
        ),

    ], className="column-dropdowns"),

    html.Div([
            dcc.Input(
            id='col-sub',
            className="inp",
            placeholder='Submit date'
            ),
            dcc.Input(
                id='col-g3m',
                className="inp info-text",
                placeholder='Good time to talk'
            ),
            dcc.Input(
                id='col-job',
                className="inp info-text",
                placeholder='Job status'
            ),
            html.Div([
            dcc.Input(
                id='col-id',
                className="inp info-text",
                placeholder='Submit ID'
            ),
            html.Div(id='id-error', className="error-div"),
            ], className="err-input-div"),
        ], className="column-inputs"),

    html.Div([
        dbc.Button(
            id="delete-row-btn",
            children="Delete row",
            color="secondary",
            size="md",
            className='button-styles delete-btn'
        ),
        dbc.Button(
            id="add-row-btn",
            children="Add row",
            color="primary",
            size="md",
            className='button-styles add-btn'
            ),
        dbc.Button(
            id="save-changes-btn",
            children="Save changes",
            color="primary",
            size="md",
            className='save-btn-class'
            ),
        # Dummy html.Div() element
        html.Div(id="dummy-div", style={'display': 'none'}),
        html.Div(id="dummy-two-div", style={'display': 'none'}),
        dag.AgGrid(
        id="my-ag-grid",
        className="ag-theme-quartz",
        columnDefs=columnDefs,
        rowData=df.to_dict("records"),
        defaultColDef={"filter": True},
        dashGridOptions={
            "rowSelection": "multiple",
            "paginationAutoPageSize": True,
            "animateRows": False,
            },
        ),
        deleted_row_ids_store
        ], className="buttons-parent")
])

# Define callback to update input color, error message, and placeholder
@app.callback(
    [Output('col-id', 'placeholder'),
     Output('id-error', 'children'),
     Output('id-error', 'style')],
    [Input('col-id', 'value'),
     Input('add-row-btn', 'n_clicks')],
    prevent_initial_call=True
)
def update_input(value, n_click):
    # Check if input is empty
    if n_click and not value:
        # Set input color to red and display error message in placeholder
        return 'Invalid ID (numeric only)', 'Please enter a valid ID', {'color': 'red', 'font-family': 'Arial', 'font-size': '14px', 'margin-left': '1rem'}
    else:
        # Set input color to black and clear error message
        return 'Submit ID', '', {'color': 'black', 'font-style': 'normal', 'font-family': 'Arial'}

# Modify the callback to append the IDs of the selected rows to the deleted_row_ids list
@app.callback(
    Output('deleted-row-ids-store', 'data'),  # Update the data stored in deleted_row_ids_store
    [Input('delete-row-btn', 'n_clicks')],
    [State('my-ag-grid', 'selectedRows'),
     State('deleted-row-ids-store', 'data')],  # Read the current state of deleted_row_ids from the store
    prevent_initial_call=True
)
def update_deleted_row_ids(n_clicks, selected_rows, deleted_row_ids):
    if n_clicks and selected_rows:
        # Extract the IDs of the selected rows
        selected_ids = [row['submission_id'] for row in selected_rows]
        # Append the IDs to the deleted_row_ids list
        deleted_row_ids += selected_ids
        print("Deleted Row IDs:", deleted_row_ids)
    return deleted_row_ids  # Return the updated deleted_row_ids list to be stored in the dcc.Store


# Define a new function to delete only deleted rows from the PostgreSQL table
def delete_rows_from_db(submission_ids):
    """Function to delete rows from the PostgreSQL table"""

    conn, cur = connect_to_db()
    try:
        for submission_id in submission_ids:
            # Construct the SQL query to delete a row from the table
            sql = "DELETE FROM calltracker_table WHERE submission_id = %s;"
            # Execute the SQL query
            cur.execute(sql, (submission_id,))

        # Commit the transaction
        conn.commit()
        print("Rows successfully deleted!", submission_ids)

    except psycopg2.Error as e:
        # Handle the error
        print("Error deleting rows:", e)

    finally:
        # Close the cursor and the connection
        cur.close()
        conn.close()


# Define a new function to insert only new rows into the PostgreSQL table
def insert_new_rows_to_db(new_rows):
    """Function to insert only new rows into the PostgreSQL table"""

    conn, cur = connect_to_db()
    try:
        for row in new_rows:

            # Check if the row already exists in the database
            cur.execute("SELECT COUNT(*) FROM calltracker_table WHERE submission_id = %s;", (row['submission_id'],))
            count = cur.fetchone()[0]

            if count == 0:  # Insert the row only if it's a new row
                # Construct the SQL query to insert a row into the table
                sql = """
                INSERT INTO calltracker_table (day, call_time, pick_up, submit_date, good_time_for_3min_talk, job, submission_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """
                # Get values for each column from the row dictionary
                values = (
                    row['day'],
                    row['call_time'],
                    row['pick_up'],
                    row['submit_date'],
                    row['good_time_for_3min_talk'],
                    row['job'],
                    row['submission_id']
                )
                # Execute the SQL query
                cur.execute(sql, values)

        # Commit the transaction
        conn.commit()
        print("New rows successfully inserted!", new_rows)

    except psycopg2.Error as e:
        # Handle the error
        print("Error inserting new rows:", e)

    finally:
        # Close the cursor and the connection
        cur.close()
        conn.close()


@app.callback(
    Output('dummy-div', 'children'),  # Dummy Output to trigger callback
    [Input('save-changes-btn', 'n_clicks')],
    [State('my-ag-grid', 'rowData'),
     State('my-ag-grid', 'selectedRows'),
     State('deleted-row-ids-store', 'data')],  # Read the stored deleted row IDs
    prevent_initial_call=True
)
def process_ag_grid_data(n_clicks, ag_grid_data, _selected_rows, stored_deleted_row_ids):
    if n_clicks and ag_grid_data:
        # Fetch existing submission IDs from the PostgreSQL table
        existing_submission_ids = fetch_existing_submission_ids_from_db()

        # Filter out rows from ag_grid_data that do not exist in the PostgreSQL table
        new_rows = [row for row in ag_grid_data if row['submission_id'] not in existing_submission_ids]

        if new_rows:  # Check if there are new rows to insert
            # Call the insert_new_rows_to_db function to insert new rows into the PostgreSQL table

            insert_new_rows_to_db(new_rows)
        else:
            print("Nothing to insert here...")

    if n_clicks and stored_deleted_row_ids:
        # Call the delete_rows_from_db function to delete rows from the PostgreSQL table
        delete_rows_from_db(stored_deleted_row_ids)
        print("Deleted Row IDs:", stored_deleted_row_ids)

    return None  # Return None to trigger the callback without updating any output


# Define callback to update graph and data table
@app.callback(
    [Output('my-ag-grid', 'deleteSelectedRows'),
    Output('my-ag-grid', 'rowData'),
    Output("my-ag-grid", "scrollTo")],
    [Input('add-row-btn', 'n_clicks'),
     Input('delete-row-btn', 'n_clicks')],
    [State('my-ag-grid', 'rowData'),
     State('col-ct', 'value'),
     State('col-pu', 'value'),
     State('col-day', 'value'),
     State('col-sub', 'value'),
     State('col-g3m', 'value'),
     State('col-job', 'value'),
     State('col-id', 'value'),],
    prevent_initial_call=True
)

def add_or_delete_row_to_ag_grid(_n_add, _n_del, data, ct_value, pu_value, day_value, sub_value, g3m_value, job_value, id_value):
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if triggered_id == 'add-row-btn':
        # Check if Submit ID input is empty
        if not id_value:
            # Return no updates to prevent adding the row
            return no_update, data, no_update

        new_row = {"day": day_value,
                   "call_time": ct_value,
                   "pick_up": pu_value,
                   "submit_date": sub_value,
                   "good_time_for_3min_talk": g3m_value,
                   "job": job_value,
                   "submission_id": id_value}
        print("New_row: ", new_row)
        new_row_index = len(data) - 1
        df_new_row = pd.DataFrame([new_row], index=[new_row_index])
        updated_table = pd.concat([pd.DataFrame(data), df_new_row])
        return False, updated_table.to_dict("records"), {"rowIndex": new_row_index}

    elif ctx.triggered_id == "delete-row-btn":
        return True, no_update, no_update


# Define callback to update graph
@app.callback(
    [Output('bar-line-chart', 'figure')],
    [Input('day-dropdown', 'value'),
     Input('my-ag-grid', 'virtualRowData')],
    [State('my-ag-grid', 'rowData')]  # State input to get the updated AgGrid data
)
def update_graph(selected_day, ag_grid_data, _vdata):
    """ updating graph function """
    global df  # Declare df as a global variable

    # Update df with the AgGrid data
    df = pd.DataFrame(ag_grid_data)

    # Check if df is empty
    if not df.empty:
        # Filter data for the selected day
        day_df = df[df['day'] == selected_day]
        # Group by "Call_time" and calculate total rows and success rate for the selected day
        grouped_df = day_df.groupby('call_time')['pick_up'].value_counts().unstack(fill_value=0)
        grouped_df['Total_Count'] = grouped_df.sum(axis=1)
        # Calculate success rate only if 'Yes' column exists in grouped_df
        if 'Yes' in grouped_df.columns:
            grouped_df['Success_Rate'] = (grouped_df['Yes'] / grouped_df['Total_Count']) * 100
        else:
            grouped_df['Success_Rate'] = 0

        # Create bar trace for total count
        bar_trace = go.Bar(
            x=grouped_df.index,
            y=grouped_df['Total_Count'],
            name='Total Dials',
            yaxis='y',
            marker=dict(color='lightblue')
        )

        # Create line trace for success rate
        line_trace = go.Scatter(
            x=grouped_df.index,
            y=grouped_df['Success_Rate'],
            name='Success Rate',
            yaxis='y2',
            mode='lines',
            line=dict(color='orange', width=2)
        )

        # Define layout
        layout = go.Layout(
            title=f'Total Dials and Success Rate on {selected_day}',
            xaxis=dict(title='Call Time'),
            yaxis=dict(title='Total Count',
                    side='left',
                    tickformat=',d',
                    range=[0, grouped_df['Total_Count'].max() + 5]),
            yaxis2=dict(title='Success Rate (%)',
                        side='right',
                        overlaying='y',
                        range=[0, 100], dtick=5),
            legend=dict(x=0, y=1, traceorder='normal'),
            margin=dict(l=50, r=50, t=50, b=50),
            height=600
        )

        # Create figure
        fig = go.Figure(data=[bar_trace, line_trace], layout=layout)
        fig.update_layout(plot_bgcolor='white')

        return [fig]
    else:
        return [go.Figure()]


if __name__ == '__main__':
    app.run_server(debug=True)
