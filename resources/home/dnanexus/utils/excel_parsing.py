import re

import pandas as pd
import vcfpy

from configs import tables, sv
from utils import misc, vcf


def open_file(file: str, file_type: str) -> pd.DataFrame:
    """Read in CSV or XLS files using pandas

    Parameters
    ----------
    file : str
        File path
    file_type : str
        File type with the file path

    Returns
    -------
    pd.DataFrame
        Dataframe created by pandas
    """

    if file_type == "csv":
        df = pd.read_csv(file)
    elif file_type == "xls":
        df = pd.read_excel(file, sheet_name=None)

    # convert the clinvar id column as a string and remove the trailing .0 that
    # the automatic conversion that pandas applies added
    if df is pd.DataFrame and "ClinVar ID" in df.columns:
        df["ClinVar ID"] = df["ClinVar ID"].astype(str)
        df["ClinVar ID"] = df["ClinVar ID"].str.removesuffix(".0")

    return df


def process_reported_variants_germline(
    df: pd.DataFrame, clinvar_resource: vcfpy.Reader
) -> pd.DataFrame:
    """Process the data from the reported variants excel file

    Parameters
    ----------
    df : pd.DataFrame
        Dataframe from parsing the reported variants excel file
    clinvar_resource : vcfpy.Reader
        vcfpy.Reader object from the Clinvar resource

    Returns
    -------
    pd.DataFrame
        Dataframe containing clinical significance info for germline variants
    """

    df = df[df["Origin"].str.lower() == "germline"]

    if df.empty:
        return None

    df.reset_index(drop=True, inplace=True)

    clinvar_ids_to_find = [
        value for value in df.loc[:, "ClinVar ID"].to_numpy()
    ]
    clinvar_info = vcf.find_clinvar_info(
        clinvar_resource, *clinvar_ids_to_find
    )

    # add the clinvar info by merging the clinvar dataframe
    df = df.merge(clinvar_info, on="ClinVar ID", how="left")

    # split the col to get gnomAD
    df[["GE", "gnomAD"]] = df[
        "Population germline allele frequency (GE | gnomAD)"
    ].str.split("|", expand=True)

    df.drop(
        ["GE", "Population germline allele frequency (GE | gnomAD)"],
        axis=1,
        inplace=True,
    )
    df.loc[:, "Variant Class"] = ""
    df.loc[:, "Actionability"] = ""
    df = df[
        [
            "Gene",
            "GRCh38 coordinates;ref/alt allele",
            "CDS change and protein change",
            "Predicted consequences",
            "Genotype",
            "Variant Class",
            "Actionability",
            "Gene mode of action",
            "clnsigconf",
            "gnomAD",
        ]
    ]

    df.fillna("", inplace=True)

    return df


def process_reported_variants_somatic(
    df: pd.DataFrame,
    lookup_refgene: tuple,
    hotspots_df: pd.DataFrame,
    cyto_df: dict,
) -> pd.DataFrame:
    """Get the somatic variants and format the data for them

    Parameters
    ----------
    df : pd.DataFrame
        Dataframe from parsing the reported variants excel file
    lookup_refgene : tuple
        Tuple of data allowing lookup in the refgene dataframes
    hotspots_df : pd.DataFrame
        Dataframe containing data from the parsed hotspots excel
    cyto_df : dict
        Dict containing dataframe of data per sheet for cytological bands

    Returns
    -------
    pd.DataFrame
        Dataframe with additional formatting for c. and p. annotation
    """

    # select only somatic rows
    df = df[df["Origin"].str.lower().str.contains("somatic")]
    df.reset_index(drop=True, inplace=True)
    df[["c_dot", "p_dot"]] = df["CDS change and protein change"].str.split(
        r"(?=;p)", n=1, expand=True
    )
    df["p_dot"] = df["p_dot"].str.slice(1)

    df["MTBP c."] = df["Gene"] + ":" + df["c_dot"]
    df["MTBP p."] = df["p_dot"].apply(misc.convert_3_letter_protein_to_1)
    df.fillna({"MTBP p.": ""}, inplace=True)

    # convert string like: NRAS:p.Gln61Arg to NRAS:p.Gln61 for lookup in the
    # hotspots excel
    df["HS p."] = df["MTBP p."].apply(
        lambda x: (
            x[: re.search(r":p.[A-Za-z]+[0-9]+", x).end()]
            if re.search(r":p.[A-Za-z]+[0-9]+", x)
            else x
        )
    )

    # populate the somatic variant dataframe with data from the refgene excel
    # file
    lookup_refgene = lookup_refgene + (
        ("HS_Total", "HS p.", hotspots_df, "HS_PROTEIN_ID", "HS_Samples"),
        ("HS_Sample", "HS p.", hotspots_df, "HS_PROTEIN_ID", "HS_Samples"),
        (
            "HS_Tumour",
            "HS p.",
            hotspots_df,
            "HS_PROTEIN_ID",
            "HS_Tumor Type Composition",
        ),
        ("Cyto", "Gene", cyto_df["Sheet1"], "Gene", "Cyto"),
    )

    for (
        new_column,
        mapping_column_target_df,
        reference_df,
        mapping_column_ref_df,
        col_to_look_up,
    ) in lookup_refgene:
        # link the mapping column to the column of data in the ref df
        reference_dict = dict(
            zip(
                reference_df[mapping_column_ref_df],
                reference_df[col_to_look_up],
            )
        )
        df[new_column] = df[mapping_column_target_df].map(reference_dict)
        df[new_column] = df[new_column].fillna("-")

    df.loc[:, "Error flag"] = ""

    df["con_count"] = df["Predicted consequences"].str.count(r"\;")

    if df["con_count"].max() > 0:
        df[["Predicted consequences", "Error flag"]] = df[
            "Predicted consequences"
        ].str.split(";", expand=True)

    df.loc[:, "LOH"] = ""

    df["VAF"] = df["VAF"].astype("str")
    df["VAF_count"] = df["VAF"].str.count(r"\;")

    if df["VAF_count"].max() > 0:
        df[["VAF", "LOH"]] = df["VAF"].str.split(";", expand=True)

    df.loc[:, "Variant class"] = ""
    df.loc[:, "TSG_NMD"] = ""
    df.loc[:, "TSG_LOH"] = ""
    df.loc[:, "Splice fs?"] = ""
    df.loc[:, "SpliceAI"] = ""
    df.loc[:, "REVEL"] = ""
    df.loc[:, "OG_3' Ter"] = ""
    df.loc[:, "Recurrence somatic database"] = ""

    df = df[
        [
            "Domain",
            "Gene",
            "GRCh38 coordinates;ref/alt allele",
            "Cyto",
            "CDS change and protein change",
            "Predicted consequences",
            "VAF",
            "LOH",
            "Error flag",
            "Alt allele/total read depth",
            "Gene mode of action",
            "Variant class",
            "TSG_NMD",
            "TSG_LOH",
            "Splice fs?",
            "SpliceAI",
            "REVEL",
            "OG_3' Ter",
            "Recurrence somatic database",
            "HS_Total",
            "HS_Sample",
            "HS_Tumour",
            "COSMIC Driver",
            "COSMIC Entities",
            "Paed Driver",
            "Paed Entities",
            "Sarc Driver",
            "Sarc Entities",
            "Neuro Driver",
            "Neuro Entities",
            "Ovary Driver",
            "Ovary Entities",
            "Haem Driver",
            "Haem Entities",
            "MTBP c.",
            "MTBP p.",
        ]
    ]
    df.rename(
        columns={
            "GRCh38 coordinates;ref/alt allele": "GRCh38 coordinates",
            "CDS change and protein change": "Variant",
        },
        inplace=True,
    )
    df.sort_values(["Domain", "VAF"], ascending=[True, False], inplace=True)
    df = df.replace([None], [""], regex=True)
    df["VAF"] = df["VAF"].astype(float)

    return df


def process_reported_SV(
    df: pd.DataFrame, lookup_refgene: tuple, type_sv: str, *check_columns
) -> pd.DataFrame:
    """Process the reported structural variants excel

    Parameters
    ----------
    df : pd.DataFrame
        Dataframe containing data from the structural variants excel
    lookup_refgene : tuple
        Tuple of data allowing lookup in the refgene dataframes
    type_sv: str
        Type of structural variant to look at in the function

    Returns
    -------
    pd.DataFrame
        Dataframe for variants with the given SV type
    """

    sv_df = df[df["Type"].str.lower().str.contains(type_sv)]
    sv_df.reset_index(drop=True, inplace=True)

    # populate the structural variant dataframe with data from the refgene
    # excel file
    for (
        new_column,
        mapping_column_target_df,
        reference_df,
        mapping_column_ref_df,
        col_to_look_up,
    ) in lookup_refgene:
        # link the mapping column to the column of data in the ref df
        reference_dict = dict(
            zip(
                reference_df[mapping_column_ref_df],
                reference_df[col_to_look_up],
            )
        )
        sv_df[new_column] = sv_df[mapping_column_target_df].map(reference_dict)
        sv_df[new_column] = sv_df[new_column].fillna("-")

    sv_df.loc[:, "Variant class"] = ""

    for column in check_columns:
        sv_df.loc[:, column] = ""

    sv_df[["Type", "Copy Number"]] = sv_df.Type.str.split(
        r"\(|\)", expand=True
    ).iloc[:, [0, 1]]
    sv_df["Copy Number"] = sv_df["Copy Number"].astype(int)
    sv_df["Size"] = sv_df.apply(lambda x: "{:,.0f}".format(x["Size"]), axis=1)
    sv_df[["Cyto 1", "Cyto 2"]] = sv_df["Chromosomal bands"].str.split(
        ";", expand=True
    )

    if list(sv_df["Type"].unique()) == ["GAIN"]:
        sv_df.sort_values(
            ["Event domain", "Copy Number"],
            ascending=[True, False],
            inplace=True,
        )
    else:
        sv_df.sort_values(
            ["Event domain", "Copy Number"],
            ascending=[True, True],
            inplace=True,
        )

    selected_col = (
        [
            "Event domain",
            "Impacted transcript region",
            "Gene",
            "GRCh38 coordinates",
            "Type",
            "Copy Number",
            "Size",
            "Cyto 1",
            "Cyto 2",
            "Gene mode of action",
            "Variant class",
        ]
        + [column for column in check_columns]
        + [
            "COSMIC Driver",
            "COSMIC Entities",
            "Paed Driver",
            "Paed Entities",
            "Sarc Driver",
            "Sarc Entities",
            "Neuro Driver",
            "Neuro Entities",
            "Ovary Driver",
            "Ovary Entities",
            "Haem Driver",
            "Haem Entities",
        ]
    )

    return sv_df[selected_col]


def process_fusion_SV(df: pd.DataFrame, lookup_refgene: tuple) -> pd.DataFrame:
    """Process the fusions from the structural variants excel

    Parameters
    ----------
    df : pd.DataFrame
        Dataframe containing the data from the structural variant excel
    lookup_refgene : tuple
        Tuple of data allowing lookup in the refgene dataframes

    Returns
    -------
    tuple
        - Dataframe containing data for the fusion structural variants
        - Max number of fusion
    """

    df_SV = df[~df["Type"].str.lower().str.contains("loss|loh|gain")]

    # split fusion columns
    df_SV["fusion_count"] = df_SV["Type"].str.count(r"\;")
    fusion_count = df_SV["fusion_count"].max()

    if fusion_count == 1:
        df_SV[["Type", "Fusion"]] = df_SV.Type.str.split(";", expand=True)
    else:
        fusion_col = []

        for i in range(fusion_count):
            fusion_col.append(f"Fusion_{i+1}")

        fusion_col.insert(0, "Type")
        df_SV[fusion_col] = df_SV.Type.str.split(";", expand=True)

    # remove prefixes for single reads and paired reads and store in separate
    # columns
    df_SV[["Paired reads", "Split reads"]] = (
        df_SV["Confidence/support"]
        .apply(misc.split_confidence_support)
        .to_list()
    )

    # get thousands separator
    df_SV["Size"] = df_SV.apply(lambda x: "{:,.0f}".format(x["Size"]), axis=1)

    # replace nan in size with empty string
    df_SV.fillna({"Size": ""}, inplace=True)
    df_SV.replace({"Size": "nan"}, {"Size": ""}, inplace=True)

    # get gene counts and look up for each gene
    df_SV["gene_count"] = df_SV["Gene"].str.count(r"\;")
    max_num_gene = df_SV["gene_count"].max() + 1

    # split gene col and create look up col for them
    if max_num_gene == 1:
        # populate the structural variant dataframe with data from the refgene
        # excel file
        for (
            new_column,
            mapping_column_target_df,
            reference_df,
            mapping_column_ref_df,
            col_to_look_up,
        ) in lookup_refgene:
            # link the mapping column to the column of data in the ref df
            reference_dict = dict(
                zip(
                    reference_df[mapping_column_ref_df],
                    reference_df[col_to_look_up],
                )
            )
            df_SV[new_column] = df_SV[mapping_column_target_df].map(
                reference_dict
            )
            df_SV[new_column] = df_SV[new_column].fillna("-")
    else:
        gene_col = []

        for i in range(max_num_gene):
            gene_col.append(f"Gene_{i+1}")

        df_SV[gene_col] = df_SV["Gene"].str.split(";", expand=True)

        for g in range(max_num_gene):
            for (
                new_column,
                mapping_column_target_df,
                reference_df,
                mapping_column_ref_df,
                col_to_look_up,
            ) in lookup_refgene:
                # link the mapping column to the column of data in the ref df
                reference_dict = dict(
                    zip(
                        reference_df[mapping_column_ref_df],
                        reference_df[col_to_look_up],
                    )
                )
                df_SV[new_column] = df_SV[mapping_column_target_df].map(
                    reference_dict
                )
                df_SV.fillna({f"{new_column}_{g+1}": "-"}, inplace=True)

    df_SV.loc[:, "Variant class"] = ""
    df_SV.loc[:, "Actionability"] = ""
    df_SV.loc[:, "Comments"] = ""

    to_lookup = ("COSMIC", "Paed", "Sarc", "Neuro", "Ovary", "Haem")
    lookup_col = [col for col in df_SV if col.startswith(to_lookup)]

    expected_columns = sv.CONFIG["expected_columns"]
    alternatives = sv.CONFIG["alternative_columns"]

    alternative_columns = tables.find_alternative_headers(
        df_SV, expected_columns, alternatives
    )

    subset_column = [
        (
            column
            if column not in alternative_columns
            else alternative_columns[column]
        )
        for column in expected_columns
    ]

    if fusion_count == 1:
        selected_col = subset_column + lookup_col

    else:
        selected_col = subset_column.insert(6, fusion_col) + lookup_col

    return df_SV[selected_col], fusion_count


def process_refgene(dfs: dict) -> dict:
    """Process the refgene group excel by replacing the NA by * in select
    columns

    Parameters
    ----------
    dfs : dict
        Dict of dataframes corresponding to the data in the sheets in the
        refgene group excel

    Returns
    -------
    dict
        Dict of processed dataframes
    """

    for df in [
        dfs["cosmic"],
        dfs["paed"],
        dfs["sarc"],
        dfs["neuro"],
        dfs["ovarian"],
        dfs["haem"],
    ]:
        if "Entities" in list(df.columns):
            df["Entities"].astype(str)
            df.fillna({"Entities": "*"}, inplace=True)
        if "Driver" in list(df.columns):
            df["Driver"].astype(str)
            df.fillna({"Driver": "*"}, inplace=True)

    return dfs
