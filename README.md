# eggd_generate_wgs_solid_cancer_workbook
This is nexflow applet to generate the workbook for WGS solid cancer variants processed by GEL

### Inputs
- variants csv file
- structural variants csv file
- html file
- b38 clinvar and index files
- RefGene_Groups xlsx file
- Hotspots csv file

### Outputs
- excel spreadsheet for variants

### How to develop applet on DNAnexus
- `git clone` the repo
- `cd` into `eggd_generate_wgs_solid_cancer_workbook`
- `dx build --nextflow --extra-args '{"access":{"project": "CONTRIBUTE", "allProjects": "VIEW"}}'` (Recommend to build with dxpy version 0.376)
- convert applet to app
```
dx build --app --from applet-xxxxxxxx --version x.x.x
dx add users app-xxxx org-emee_1
```
### How to run the applet
Example command
```
dx run app-xxxx \
-ihotspots="project-GkG4Zf84Yj359Q9JYbbqbFpy:file-GkG4q6j4Yj36y2VXZzqB09J5" \
-irefgene_group="project-GkG4Zf84Yj359Q9JYbbqbFpy:file-GkkJxJQ4Yj36VF6PvkJF5Q1X" \
-iclinvar="project-Fkb6Gkj433GVVvj73J7x8KbV:file-GjP2v0j42VYfY5qfYGVKxy79" \
-iclinvar_index="project-Fkb6Gkj433GVVvj73J7x8KbV:file-GjP2vG842VYjBz0VfGQBZ7F8" \
-inextflow_pipeline_params="--file_path=dx://project-xxx:/xxx/xxx" # file path where csv and html are located
```
:point_right: make sure the ref files specified in the command line are most recent deployed version in production.

:triangular_flag_on_post: DNAnexus told me that the next released dxpy version will allow to specify the input URI with file ID in the config file. So, recommended to update the nextflow.config file with fileID URL once the new dxpy version is released so that it is not required to to specify them in the command line :triangular_flag_on_post:
