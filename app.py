import pandas as pd
import yfinance as yf
from datetime import datetime
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, dash_table, callback
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from utils import *

# start dash app
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
)
server = app.server

# --------------------- APP LAYOUT ------------------ #
# get stock list from wikipedia
storage_options = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
}
drop_down_options = pd.read_html(
    "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    storage_options=storage_options,
)[0]["Symbol"].values.tolist()
drop_down_options.extend(["QQQ", "SPY"])
# drop_down_options = ["QQQ", "AAPL", "GOOG", "MSFT", "TSLA", "META"]

app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    html.H1("Stock Comparison Dashboard", className="text-center"),
                    width=12,
                )
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dcc.Store(id="stocks-data"),
                        html.Label(
                            "Select stock symbol and date range",
                            style={"font-weight": "bold"},
                        ),
                        # Dropdown for selecting stocks
                        dcc.Dropdown(
                            id="stocks-dropdown",
                            options=["AAPL", "QQQ"],
                            value=["AAPL", "QQQ"],
                            placeholder="Search stock symbol",
                            multi=True,
                            className="mb-2",
                        ),
                    ],
                    lg=7,
                    sm=12,
                    align="end",
                ),
                dbc.Col(
                    [
                        # Date range picker
                        dcc.DatePickerRange(
                            id="date-range-picker",
                            max_date_allowed=datetime.now(),
                            start_date=datetime(2020, 1, 1),
                            end_date=datetime.now(),
                            className="m-2",
                        ),
                        dbc.Button(
                            "Get Data",
                            n_clicks=0,
                            id="get-data-button-state",
                            className="m-2",
                        ),
                    ],
                    lg=5,
                    sm=12,
                    align="end",
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H6("Plot options"),
                        dbc.RadioItems(
                            id="comparison-plot-option",
                            options=[
                                {"label": "Price", "value": "price"},
                                {"label": "Cummulative return", "value": "cum_ret"},
                                {"label": "Drawdown", "value": "drawdown"},
                                {"label": "Correlation matrix", "value": "corr_mat"},
                                {
                                    "label": "3M rolling cumulative return",
                                    "value": "3mcr",
                                },
                                {
                                    "label": "6M rolling cumulative return",
                                    "value": "6mcr",
                                },
                                {"label": "3M rolling volatility", "value": "3mrv"},
                                {"label": "6M rolling volatility", "value": "6mrv"},
                                {"label": "3M rolling cvar", "value": "3mcvar"},
                                {"label": "6M rolling cvar", "value": "6mcvar"},
                                {"label": "3M rolling sharpe ratio", "value": "3msr"},
                                {"label": "6M rolling sharpe ratio", "value": "6msr"},
                            ],
                            value="price",
                        ),
                    ],
                    lg=3,
                    md=4,
                    sm=12,
                    align="center",
                ),
                dbc.Col(
                    dcc.Graph(id="comparison-plot"), lg=9, md=8, sm=12, align="center"
                ),
            ]
        ),
        dbc.Row(dbc.Col(id="summary-table")),
    ],
    fluid=True,
)


# --------------------- CALL BACKS ------------------ #
@callback(
    Output("stocks-dropdown", "options"),
    [Input("stocks-dropdown", "search_value"), State("stocks-dropdown", "value")],
)
def update_dropdown(search_value, existing_value):
    print(search_value)
    if not search_value:
        raise PreventUpdate
    return [
        o
        for o in drop_down_options
        if (search_value in o) or (o in (existing_value or []))
    ]


@callback(
    Output("stocks-data", "data"),
    [
        Input("get-data-button-state", "n_clicks"),
        State("stocks-dropdown", "value"),
        State("date-range-picker", "start_date"),
        State("date-range-picker", "end_date"),
    ],
)
def fetch_data(n_clicks, tickers, start_date, end_date):
    # slice date string from date range inputs
    start = start_date[:10]
    end = end_date[:10]

    # get data from yahoo finance
    price_df = yf.download(tickers=tickers, start=start, end=end)["Close"]
    # price_df = pd.read_csv("./data/tech_assets.csv", index_col=0).loc[:, tickers]

    # convert Series to DataFrame if only one asset was requested
    if isinstance(price_df, pd.Series):
        price_df = price_df.to_frame(tickers[0])

    # convert dataframe to dictionary
    price_data = price_df.to_dict("tight")

    return price_data


@callback(
    Output("comparison-plot", "figure"),
    [
        Input("get-data-button-state", "n_clicks"),
        Input("stocks-data", "data"),
        State("stocks-dropdown", "value"),
        State("date-range-picker", "start_date"),
        State("date-range-picker", "end_date"),
        Input("comparison-plot-option", "value"),
    ],
)
def plot(n_clicks, data, tickers, start_date, end_date, option):
    df = pd.DataFrame.from_dict(data, orient="tight")
    df.index.name = "Date"
    start = start_date[:10]
    end = end_date[:10]
    doi = df.loc[start:end, tickers].copy()
    returns = prep_returns(doi)

    if option == "price":
        return plot_stats(doi)
    elif option == "cum_ret":
        return plot_stats(doi, option)
    elif option == "drawdown":
        return plot_stats(doi, option)
    elif option == "corr_mat":
        return plot_stats(returns, option)
    elif option == "3mcr":
        stats = get_rolling_stats(returns, 63, stat="cum_ret")
        fig = plot_rolling_stats(stats, "cum_ret")
        fig.update_layout(title="<b>3 Months Rolling Cumulative Return</b>")
        return fig
    elif option == "6mcr":
        stats = get_rolling_stats(returns, 126, stat="cum_ret")
        fig = plot_rolling_stats(stats, "cum_ret")
        fig.update_layout(title="<b>6 Months Rolling Cumulative Return</b>")
        return fig
    elif option == "3mrv":
        stats = get_rolling_stats(returns, 63, stat="vol")
        fig = plot_rolling_stats(stats, "vol")
        fig.update_layout(title="<b>3 Months Rolling Volatility</b>")
        return fig
    elif option == "6mrv":
        stats = get_rolling_stats(returns, 126, stat="vol")
        fig = plot_rolling_stats(stats, "vol")
        fig.update_layout(title="<b>6 Months Rolling Volatility</b>")
        return fig
    elif option == "3mcvar":
        stats = get_rolling_stats(returns, 63, stat="cvar")
        fig = plot_rolling_stats(stats, "cvar")
        fig.update_layout(title="<b>3 Months Rolling CVAR(5%)</b>")
        return fig
    elif option == "6mcvar":
        stats = get_rolling_stats(returns, 126, stat="cvar")
        fig = plot_rolling_stats(stats, "cvar")
        fig.update_layout(title="<b>6 Months Rolling CVAR(5%)</b>")
        return fig
    elif option == "3msr":
        stats = get_rolling_stats(returns, 63, stat="sr")
        fig = plot_rolling_stats(stats, "sr")
        fig.update_layout(title="<b>3 Months Rolling Sharpe Ratio</b>")
        return fig
    elif option == "6msr":
        stats = get_rolling_stats(returns, 126, stat="sr")
        fig = plot_rolling_stats(stats, "sr")
        fig.update_layout(title="<b>6 Months Rolling Sharpe Ratio</b>")
        return fig


@callback(
    Output("summary-table", "children"),
    [
        Input("get-data-button-state", "n_clicks"),
        Input("stocks-data", "data"),
        State("stocks-dropdown", "value"),
        State("date-range-picker", "start_date"),
        State("date-range-picker", "end_date"),
    ],
)
def summary_table(n_clicks, data, tickers, start_date, end_date):
    df = pd.DataFrame.from_dict(data, orient="tight")
    df.index.name = "Date"
    start = start_date[:10]
    end = end_date[:10]
    doi = df.loc[start:end, tickers].copy()
    returns = prep_returns(doi)

    summary_df = get_summary_df(returns)
    summary_df.index.name = "Ticker"
    summary_df = summary_df.reset_index()
    data = summary_df.to_dict("records")
    data_col = [{"name": col, "id": col} for col in summary_df.columns]
    table = [
        html.Label("Summary table", style={"font-weight": "bold"}),
        dash_table.DataTable(
            data,
            data_col,
            style_table={"overflowX": "auto"},
        ),
    ]
    return table


if __name__ == "__main__":
    app.run()
