import json
from datetime import datetime

def html_make_clickable(row) -> str:
    text = row['Name']
    url = row['URL']
    return f'<a href="{url}" target="_blank">{text}</a>'

def html_construct_list(params: dict) -> str:
    html_list_items = "".join(f"<li><b>{key}</b>: {val}</li>" for key, val in params.items())
    return f'<ul>{html_list_items}</ul>\n'

def export_to_file(df, filename: str, config: dict, styled_df):
    now = datetime.now()
    formatted_now = now.strftime("%B %d, %Y %H:%M")
    iso_filename_timestamp = now.strftime("%Y-%m-%d_%H%M%S")

    currency = config["currency"]
    params = config["search_parameters"]
    
    mean_total_price = df["Total Price"].mean()
    median_total_price = df["Total Price"].median()
    result_count = df.shape[0]

    search_params = {
        "Check-In Date": params["checkin"],
        "Check-Out Date": params["checkout"],
        "Guest Count": str(params["adult_count"]),
        "Price Range (approximate)": f"${params['price_min']} - ${params['price_max']}",
        "Area (geographical bounding box)": str(params["search_box"])
    }

    stats = {
        f"Median Total Price ({currency})": f"${median_total_price:.2f}",
        f"Mean Total Price ({currency})": f"${mean_total_price:.2f}"
    }

    html_search_param_list = html_construct_list(search_params)
    html_stat_list = html_construct_list(stats)

    html_table = styled_df.to_html(index=False, escape=False, justify="end")

    with open(f"{filename}-{iso_filename_timestamp}.html", 'w') as f:
        f.write("<html>\n<head><title>BnBPuller Results</title></head>\n<body>\n")
        f.write(f"<h1>Search Query Summary ({formatted_now})</h1>\n")
        f.write("<h2>Search Parameters:</h2>\n")
        f.write(html_search_param_list)
        f.write("<h2>Price Analysis:</h2>\n")
        f.write(f"<h3>{result_count} results</h3>\n")
        f.write(html_stat_list)
        f.write(html_table)
        f.write("\n</body>\n</html>")

def export_monitor_report(stats_df, filename: str):
    labels = stats_df['timestamp'].tolist()
    mean_prices = stats_df['mean_price'].tolist()
    median_prices = stats_df['median_price'].tolist()
    counts = stats_df['result_count'].tolist()
    
    chart_js_script = f"""
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        const labels = {json.dumps(labels)};
        
        const priceCtx = document.getElementById('priceChart').getContext('2d');
        new Chart(priceCtx, {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{
                        label: 'Mean Price',
                        data: {json.dumps(mean_prices)},
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    }},
                    {{
                        label: 'Median Price',
                        data: {json.dumps(median_prices)},
                        borderColor: 'rgb(255, 99, 132)',
                        tension: 0.1
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Price Trends Over Time'
                    }}
                }}
            }}
        }});

        const countCtx = document.getElementById('countChart').getContext('2d');
        new Chart(countCtx, {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'Result Count',
                    data: {json.dumps(counts)},
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderColor: 'rgb(54, 162, 235)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Available Results Count Over Time'
                    }}
                }}
            }}
        }});
    </script>
    """
    
    with open(f"{filename}.html", 'w') as f:
        f.write("<html>\n<head><title>Airbnb Monitor Report</title></head>\n<body>\n")
        f.write("<h1>Airbnb Monitor Report</h1>\n")
        f.write('<div style="width: 80%; margin: auto;">\n')
        f.write('  <canvas id="priceChart"></canvas>\n')
        f.write('</div>\n')
        f.write('<div style="width: 80%; margin: auto; margin-top: 50px;">\n')
        f.write('  <canvas id="countChart"></canvas>\n')
        f.write('</div>\n')
        f.write(chart_js_script)
        f.write("\n</body>\n</html>")
