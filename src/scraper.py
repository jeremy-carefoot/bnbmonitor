import pyairbnb

def get_results(config):
    params = config["search_parameters"]
    results = pyairbnb.search_all(
        currency=config["currency"],
        language=config["language"],
        zoom_value=1,
        check_in=params["checkin"],
        check_out=params["checkout"],
        adults=params["adult_count"],
        price_min=params["price_min"],
        price_max=params["price_max"],
        sw_long=params["search_box"][0],
        sw_lat=params["search_box"][1],
        ne_long=params["search_box"][2],
        ne_lat=params["search_box"][3],
    )
    return results
