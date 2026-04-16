import pandas as pd

def db_results_to_df(db_rows):
    headers = ["Name", "Rating", "Bed Count", "URL", "Total Price"]
    data = []
    for row in db_rows:
        data.append([
            row["name"],
            row["rating"],
            row["bed_count"],
            row["room_url"],
            row["total_price"]
        ])
    
    df = pd.DataFrame(data, columns=headers)
    # Sort by price since DB might not be sorted
    df = df.sort_values(by="Total Price").reset_index(drop=True)
    return df

def style_df(df, currency, html_make_clickable_fn):
    # Make name column clickable and remove URL column
    df_copy = df.copy()
    df_copy["Name"] = df_copy[["Name", "URL"]].apply(html_make_clickable_fn, axis=1)
    # Format Total Price
    df_copy["Total Price"] = df_copy['Total Price'].apply(lambda x: f'${x:.2f}')
    df_copy.rename(columns={'Total Price': f'Total Price ({currency})'}, inplace=True)
    new_df = df_copy.drop(columns=["URL"])

    return new_df
