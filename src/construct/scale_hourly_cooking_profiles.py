import pandas as pd

import util


def get_hourly_cooking(annual_demand, cooking_profiles, regions, first_year, final_year, demand_key, out_path):
    def _fill_empty_country(df, country_neighbour_dict):
        df = df.unstack('country_code')
        for country, neighbours in country_neighbour_dict.items():
            df[country] = df[neighbours].mean(axis=1)
        return df.stack().rename('cooking_profiles')

    demand_key = demand_key.replace("-", "_")
    annual_demand_df = util.read_tdf(annual_demand)
    cooking_profiles_df = pd.read_csv(
        cooking_profiles, index_col=[0, 1, 2], parse_dates=[0], squeeze=True
    )
    profiles = []
    for year in range(first_year, final_year + 1):
        this_year_annual_demand_df = annual_demand_df.xs(year, level='year').droplevel('unit')

        this_year_cooking_profiles_df = cooking_profiles_df.xs(year, level='year')
        region_df = pd.read_csv(regions, index_col=0)

        # We merge commercial and household cooking demands together
        annual_cooking = (
            this_year_annual_demand_df
            .xs(('heat_demand', demand_key), level=('dataset', 'end_use'))
            .sum(level='id')
        )
        annual_cooking = (
            pd.merge(
                annual_cooking.to_frame('annual_cooking'),
                region_df,
                left_index=True, right_index=True
            )
            .set_index('country_code', append=True)
        )
        # Fill missing countries based on nearest neighbours in the same timezone
        this_year_cooking_profiles_df = _fill_empty_country(
            this_year_cooking_profiles_df,
            {'ALB': ['SRB'], 'MKD': ['SRB'], 'GRC': ['BGR'], 'CYP': ['BGR'],
            'BIH': ['SRB', 'HRV'], 'MNE': ['SRB', 'HRV'], 'ISL': ['GBR']}
        )
        df = pd.merge(this_year_cooking_profiles_df, annual_cooking, left_index=True, right_index=True)
        hourly_cooking = df['annual_cooking'].mul(df['cooking_profiles'])
        hourly_cooking = (-1) * hourly_cooking.droplevel('country_code').unstack()
        util.verify_profiles(hourly_cooking, demand_key, this_year_annual_demand_df)
        if demand_key == 'cooking':
            # stack and unstack to ensure we filter against the maximum of the whole dataset,
            # not on a per-region basis
            hourly_cooking = util.filter_small_values(
                hourly_cooking.stack(), rel_tol=1e-4
            ).unstack()
        profiles.append(hourly_cooking)

    pd.concat(profiles, sort=True).to_csv(out_path)


if __name__ == "__main__":
    get_hourly_cooking(
        annual_demand=snakemake.input.annual_demand,
        cooking_profiles=snakemake.input.cooking_profiles,
        regions=snakemake.input.regions,
        first_year=snakemake.params.first_year,
        final_year=snakemake.params.final_year,
        demand_key=snakemake.params.demand_key,
        out_path=snakemake.output[0],
    )
