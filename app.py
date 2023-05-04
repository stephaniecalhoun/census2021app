import dash
import dash_table
import pandas as pd
import requests
from dash import dcc as dcc
from dash import html as html
from dash.dependencies import Input, Output

server = app.server

# Define the font family and size
FONT_FAMILY = 'Arial, sans-serif'
FONT_SIZE = '16px'

# get dimensions
dimensions_URL = requests.get("https://api.beta.ons.gov.uk/v1/population-types/UR/dimensions")
results = dimensions_URL.json()
dimensions = []
for dimension in results.get("items"):
    dimensions.append({"label": dimension.get("label"), "value": dimension.get("id")})
filteroutList = ['Country of birth (extended) (190 categories)','Country of birth (60 categories)',
              'Industry (current) (88 categories)','Industry (former) (17 categories)',
              'Occupation (current) (105 categories)','Occupation (former) (11 categories)',
              'Passports held (52 categories)','Employment history (4 categories)','National identity (detailed) (73 categories)']
dimensions = [d for d in dimensions if d['label'] not in filteroutList]

# Define the layout of the application
app = dash.Dash(__name__)
app.layout = html.Div([
    html.H1('Enter a postcode below to see 2021 Census results for the associated Lower Super Output Area (LSOA)',
            style={'font-family': FONT_FAMILY, 'font-size': FONT_SIZE}),
    html.P(
        'Note: LSOAs are small geographic areas of 1,500 people on average. There are 33,755 LSOAs in England.',
        style={'font-family': FONT_FAMILY, 'font-size': FONT_SIZE}),
    dcc.Input(id='input', value='', type='text', style={'font-family': FONT_FAMILY, 'font-size': FONT_SIZE}),
    html.Br(),
    html.H1('Choose variable here', style={'font-family': FONT_FAMILY, 'font-size': FONT_SIZE}),
    dcc.Dropdown(
        id='dimension-dropdown',
        options=dimensions,
        value=dimensions[0]["value"],
        style={'font-family': 'Arial'}
    ),
    html.Br(),
    html.Button('Submit', id='submit', n_clicks=0, style={'font-family': FONT_FAMILY, 'font-size': FONT_SIZE}),
    html.Br(),
    html.Br(),
    dash_table.DataTable(id='output', style_cell={'fontFamily': 'Arial', 'fontSize': '16px'}),
    html.Br(),
    html.Br(),
    html.P(
        'These are estimates from the Office of National Statistics (ONS) as of Census day March 21 2021.',
        style={'font-family': FONT_FAMILY, 'font-size': '13px'}),
    html.P(
        'For statistical disclosure control, the ONS has made small changes to some small counts.',
        style={'font-family': FONT_FAMILY, 'font-size': '13px'})
])


# Define the callback of the application
@app.callback(
    Output('output', 'data'),
    [Input('submit', 'n_clicks'), Input('dimension-dropdown', 'value')],
    [dash.dependencies.State('input', 'value')]
)
def gen_data(n_clicks, dimension, postcode):
    if postcode is None:
        return []
    root_URL = "https://api.beta.ons.gov.uk/v1/population-types/UR/census-observations?area-type=lsoa,"
    response = requests.get(f'https://api.postcodes.io/postcodes/{postcode}')
    if response.status_code == 200:
        result = response.json()
        code = result['result']['codes']['lsoa']
        code_name = result['result']['lsoa']
        england_API = requests.get(
            'https://api.beta.ons.gov.uk/v1/population-types/UR/census-observations?area-type=ctry,E92000001&dimensions=' + dimension)
        response_API = requests.get(root_URL + code + "&dimensions=" + dimension)
        if response_API.status_code == 200 and england_API.status_code == 200:
            results = response_API.json()
            england_results = england_API.json()
            summary = []
            summary_england = []
            if results.get("observations") is not None and england_results.get("observations") is not None:
                for observation in results.get("observations"):
                    summary.append(
                        {"dim": observation.get("dimensions"), "observation": observation.get("observation")})
                for observation in england_results.get("observations"):
                    summary_england.append(
                        {"dim": observation.get("dimensions"), "observation_england": observation.get("observation")})
                lsoa_df = pd.DataFrame(summary)
                england_df = pd.DataFrame(summary_england)
                lsoa_df['Category'] = lsoa_df.apply(
                    lambda row: row['dim'][1].get('option').split(':')[0] if row['dim'][0].get(
                        'id') == 'highest_qualification' else row['dim'][1].get('option'), axis=1)
                england_df['Category'] = england_df.apply(
                    lambda row: row['dim'][1].get('option').split(':')[0] if row['dim'][0].get(
                        'id') == 'highest_qualification' else row['dim'][1].get('option'), axis=1)
                df = lsoa_df.merge(england_df, on='Category', how='left')
                df = df[(df.Category != 'Does not apply')]
                sum_all_rows = df['observation'].sum()
                sum_all_rows_england = df['observation_england'].sum()
                df['Share of residents'] = df.apply(lambda row: round(row['observation'] / sum_all_rows * 100), axis=1)
                df['Share of residents in England'] = df.apply(
                    lambda row: round(row['observation_england'] / sum_all_rows_england * 100), axis=1)
                df['Share of residents'] = df['Share of residents'].astype(str) + '%'
                df['Share of residents in England'] = df['Share of residents in England'].astype(str) + '%'
                df = df.rename(columns={"observation": "Number of residents in " + code_name,
                                        "Share of residents": "Share of residents " + code_name})
                df = df[['Category', 'Number of residents in ' + code_name, 'Share of residents ' + code_name,
                         'Share of residents in England']]
                return df.to_dict('records')
            else:
                return []
        if response_API.status_code != 200:
            return []
    else:
        print(f'Error getting output area for postcode {postcode}.')


# Run the application
if __name__ == '__main__':
    app.run_server(debug=True)
