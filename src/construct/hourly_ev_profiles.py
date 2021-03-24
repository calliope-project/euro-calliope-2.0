import pandas as pd


def get_hourly_ev_profiles(
    regions_path, ev_profiles_path, dataset_name, demand_range, model_year, out_path
):
    """
    Fill empty countries and map EV profiles to national subregions.
    Profiles are already normalised relative to total number of vehicles in
    the fleet.
    """
    regions_df = pd.read_csv(regions_path).set_index(['id', 'country_code'])
    ev_profiles_df = (
        pd.read_csv(ev_profiles_path, index_col=[0, 1, 2], parse_dates=[0])
        .xs(model_year, level='year')
    )
    # Demand is normalised to just get the fluctuations in demand rather than absolute values
    # We create two demand profiles, to create a min/max range of total demand that can be met
    # in a timestep (or collection of timesteps)
    if "demand" in dataset_name:
        if "light" in dataset_name:
            ev_profile = (
                ev_profiles_df
                .demand
                .div(ev_profiles_df.demand.sum(level='country_code'))
                .mul(demand_range[dataset_name.split("-")[1]])
            )
        elif "heavy" in dataset_name:
            ev_profile = (
                ev_profiles_df
                .assign(static_demand=1)
                .static_demand
                .div(len(ev_profiles_df.index.get_level_values('datetime').unique()))
                .mul(demand_range[dataset_name.split("-")[1]])
            )
    # % plugged-in EVs is already normalised
    elif dataset_name == 'plugin':
        ev_profile = ev_profiles_df.plugin

    def _fill_empty_country(df, country_neighbour_dict):
        df = df.unstack('country_code')
        for country, neighbours in country_neighbour_dict.items():
            df[country] = df[neighbours].mean(axis=1)
        return df.stack().rename('ev_profiles')

    # Fill missing countries based on nearest neighbours in the same timezone
    ev_profile = _fill_empty_country(
        ev_profile,
        {'ALB': ['HRV'], 'MKD': ['HRV'], 'GRC': ['ROU'], 'CYP': ['ROU'], 'BGR': ['ROU'],
         'BIH': ['HRV', 'HUN'], 'MNE': ['HRV'], 'ISL': ['GBR'], 'SRB': ['HUN']}
    )
    ev_profile = (
        ev_profile.align(regions_df)[0]
        .droplevel('country_code')
        .unstack('id')
    )
    # to naive timezone, to match all other CSVs in the model
    ev_profile.index = ev_profile.index.tz_localize(None)
    ev_profile.to_csv(out_path)


if __name__ == "__main__":
    get_hourly_ev_profiles(
        regions_path=snakemake.input.regions,
        ev_profiles_path=snakemake.input.ev_profiles,
        dataset_name=snakemake.params.dataset_name,
        demand_range=snakemake.params.demand_range,
        model_year=snakemake.params.model_year,
        out_path=snakemake.output[0],
    )
