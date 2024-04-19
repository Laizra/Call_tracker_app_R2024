import dash
import dash_ag_grid as dag
from dash import html, dcc, Input, Output, State, no_update, callback_context
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go

# Initialize Dash app
app = dash.Dash(__name__)

# Initialize DataFrame
df = pd.read_csv("new_tracker.csv")
graph = dcc.Graph(id='bar-line-chart', figure={})

# Filter out null values from 'Day' column
available_days = df['Day'].dropna().unique()
call_times = df['Call_time'].dropna().unique()
pick_up = df['Pick_up'].dropna().unique()

columnDefs = [
    {"field": c, "editable": True,
        "checkboxSelection": True,} for c in df.columns
]

# Define layout
app.layout = html.Div([
    dcc.Dropdown(
        id='day-dropdown',
        options=[{'label': day, 'value': day} for day in available_days],
        value='Sunday',
        clearable=False
    ),
    html.Br(),
    html.Br(),
    html.Div([
        graph
    ], id="chart-breakdown"),
    html.Br(),
    html.Br(),
    html.Div([
        dcc.Dropdown(
            id='col-ct',
            options=[{'label': ct, 'value': ct} for ct in call_times],
            value='0:00 PM',
            clearable=False,
            className='drop-columns'
        ),
        dcc.Dropdown(
            id='col-pu',
            options=[{'label': pu, 'value': pu} for pu in pick_up],
            value='Yes',
            clearable=False,
            className='drop-columns'
        ),
        dcc.Dropdown(
            id='col-day',
            options=[{'label': d, 'value': d} for d in available_days],
            value='Sunday',
            clearable=False,
            className='drop-columns'
        ),
    ], className="column-dropdowns"),

    html.Div([
        dbc.Button(
            id="delete-row-btn",
            children="Delete row",
            color="secondary",
            size="md",
            className='mt-3 me-1'
        ),
        dbc.Button(
            id="add-row-btn",
            children="Add row",
            color="primary",
            size="md",
            className='mt-3'
            ),
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

        ])
])

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
     State('col-day', 'value')],
    prevent_initial_call=True
)

def add_or_delete_row_to_ag_grid(_n_add, _n_del, data, ct_value, pu_value, day_value):
    """ add and delete rows """
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if triggered_id == 'add-row-btn':
        new_row = {"Submit_date": "", "Call_time": ct_value, "Pick_up": pu_value, "Day": day_value, "Good_time_for_3min_talk": "", "Job": "", "Submission_ID": "0"}
        new_row_index = len(data) - 1
        df_new_row = pd.DataFrame([new_row], index=[new_row_index])
        updated_table = pd.concat([pd.DataFrame(data), df_new_row])
        return False, updated_table.to_dict("records"), {"rowIndex": new_row_index}

    elif ctx.triggered_id == "delete-row-btn":
        return True, no_update, {"rowIndex": len(data) -3}


# Define callback to update graph
@app.callback(
    [Output('bar-line-chart', 'figure')],
    [Input('day-dropdown', 'value'),
     Input('my-ag-grid', 'virtualRowData')],
    [State('my-ag-grid', 'rowData')]  # State input to get the updated AgGrid data
)
def update_graph(selected_day, ag_grid_data, vdata):
    """ updating graph function """
    global df  # Declare df as a global variable

    # Update df with the AgGrid data
    df = pd.DataFrame(ag_grid_data)

    # Filter data for the selected day
    day_df = df[df['Day'] == selected_day]

    # Group by "Call_time" and calculate total rows and success rate for the selected day
    grouped_df = day_df.groupby('Call_time')['Pick_up'].value_counts().unstack(fill_value=0)
    grouped_df['Total_Count'] = grouped_df.sum(axis=1)
    grouped_df['Success_Rate'] = (grouped_df['Yes'] / grouped_df['Total_Count']) * 100

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
if __name__ == '__main__':
    app.run_server(debug=True)