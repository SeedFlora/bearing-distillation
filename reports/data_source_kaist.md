# KAIST rotating-machine datasets (Jung et al., Data in Brief 2023): documentation verification

Prepared 2026-11-07 for the project "Transferability-Aware Cross-Modal Distillation for Current-Only Bearing Fault Diagnosis under Unseen Operating Conditions" (planned KAIST replication). Every web source below was accessed on **2026-11-07**. Claims are tagged with a source key from Section 1 plus a location (page / section / table / field). Page numbers refer to the journal PDF (pages 1-19).

The report keeps three kinds of statement apart:

- **Documented**: what the paper, the Mendeley records or the older description PDFs actually say.
- **Observed**: what the internal metadata of the published varying-load files shows. These were read-only checks on local copies whose SHA-256 matches the Mendeley values.
- **Inference**: my interpretation, always labelled as such.

---

## 0. Key findings

1. **Licence and versions.** All four Mendeley records are **CC BY 4.0**. The cited versions are the latest ones: varying-load `ztmf3m7h5x` **v6** (2023-02-08) and varying-speed `vxkj334rzv` / `x3vhp8t6hg` / `j8d8pfkvj2` **v7** (2023-02-08, 2023-02-09, 2023-02-09). Each record holds only zip files and has no sub-folders. The data zips have been byte-identical (same SHA-256) in every version since v1 (2022-08-15) [M-VL, M-S1..3, M-HIST].
2. **Synchronisation is not documented for vibration and current.** The paper says vibration came from a Siemens SCADAS Mobile 5PM50 and current from NI modules. These are separate systems [P p.4 §2; p.9]. "Simultaneously" is used only for the four accelerometers [P p.4 §2]. "Synchronized" is used only for the speed data in the varying-speed part [P p.3; p.9]. Nothing is said about a shared clock or trigger.
3. **Observed: two unsynchronised clocks.** In the varying-load files, the vibration MAT files carry Test.Lab absolute start times and the current/temperature TDMS files carry FlexLogger `wf_start_time`. The difference between them is nearly constant within each day: 203.0 s (2021-06-25), 197.9 s (2021-06-28) and 206.6 s (2021-06-30). Inference: the two systems ran on clocks about 3.3-3.4 min apart and were started at nearly the same time. After removing the daily offset, 42 of 45 pairs line up within 2.8 s (34 within 0.25 s). Sample-level alignment is not available.
4. **Observed: three serious data issues that the documentation does not mention.**
   - **(a) Outer race, one current phase only.** All 9 outer-race (BPFO) TDMS files hold current data on **only one of three channels**.
   - **(b) Outer race 0.3 mm not recorded at the same time.** For BPFO 0.3 mm at all three loads, the vibration and current recordings were **not concurrent** (about 32 min apart).
   - **(c) Inner race at 0 Nm, current files apparently swapped.** The TDMS files `0Nm_BPFI_03.tdms` and `0Nm_BPFI_10.tdms` appear **swapped**: their internal log names and their recording times point to 1.0 mm and 0.3 mm respectively.
5. **Observed: durations differ from the documentation.** The paper gives 120 s for normal and 60 s for faulty states [P p.4; Table 2 p.17]. In the files:
   - misalignment and unbalance runs are **120 s**;
   - the 0 Nm normal run is **300 s**;
   - bearing-fault runs are 60 s, as documented.
6. **Observed: sampling rates.** Vibration is exactly 25,600 Hz and acoustic 51,200 Hz. Current and temperature in the TDMS files are about **25,608.2 Hz** (`wf_increment` = 3.905e-05 s), not exactly 25.6 kHz. Temperature changes only about 4.8 times per second (a held, slow thermocouple signal). The temperature module recorded in the files is an **NI 9210**. The paper says NI 9211. Both are 14 S/s thermocouple modules [NI9210, NI9211].
7. **Independent units are not documented.** The paper never states how many physical bearings exist per class or severity, or whether the same faulty bearing was reused across loads. "The corresponding fault-seeded bearing" is singular [P p.15 §3.2], and the figures show one specimen per severity [P Fig. 6 p.15] and one per state [P Fig. 9 p.18]. Inference from recording times: each severity was mounted once and run at 0, 2 and 4 Nm in one block. For bearing-grouped cross-fitting, KAIST therefore offers **at most one specimen per (fault type, severity)** and apparently a single healthy bearing.
8. **The naming scheme is documented but not followed exactly.** The documented pattern is `aaaaNm_bbbb_cccc.mat/.tdms` [M-VL description; P pp.4-8]. Five vibration files are spelled `2Nm_Unbalalnce_*.mat`. None of the files contains a literal "Time Stamp" column: time is implicit (start time plus increment).

---

## 1. Sources and access achieved

| Key | Source | URL(s) (accessed 2026-11-07) | Access achieved |
|---|---|---|---|
| P | Jung, Kim, Yun, Bae, Park, "Vibration, acoustic, temperature, and motor current dataset of rotating machine under varying operating conditions for fault diagnosis", *Data in Brief* 48 (2023) 109049, doi:10.1016/j.dib.2023.109049, PMCID PMC10036499, PMID 36969976 | PDF (PMC Open Access, md5 98979fb92cbfc27e17317a9de40ef3bc verified): https://pmc-oa-opendata.s3.amazonaws.com/PMC10036499.1/PMC10036499.1.pdf ; JATS XML: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=10036499&rettype=xml ; HTML: https://pmc.ncbi.nlm.nih.gov/articles/PMC10036499/ ; figures gr1, gr5, gr6, gr7, gr9 from https://pmc-oa-opendata.s3.amazonaws.com/PMC10036499.1/ | **full_text** (publisher PDF via PMC). ScienceDirect https://www.sciencedirect.com/science/article/pii/S2352340923001671 returned HTTP 403 (robot check), so it was not read. |
| CR | Crossref metadata and BibTeX; corrections check | https://api.crossref.org/works/10.1016/j.dib.2023.109049 ; https://doi.org/10.1016/j.dib.2023.109049 (BibTeX) ; https://api.crossref.org/works?filter=updates:10.1016/j.dib.2023.109049 | metadata |
| PMCJ | PMC OA metadata (licence, retraction flag) | https://pmc-oa-opendata.s3.amazonaws.com/PMC10036499.1/PMC10036499.1.json | metadata |
| M-VL | Mendeley Data `ztmf3m7h5x` v6 (varying load) | https://data.mendeley.com/public-api/datasets/ztmf3m7h5x?version=6 ; https://data.mendeley.com/public-api/datasets/ztmf3m7h5x/files?folder_id=root&version=6 ; https://data.mendeley.com/public-api/datasets/ztmf3m7h5x/folders/6 ; landing page https://data.mendeley.com/datasets/ztmf3m7h5x/6 | full record metadata and file listing |
| M-S1 | Mendeley Data `vxkj334rzv` v7 (varying speed, Subset1) | https://data.mendeley.com/public-api/datasets/vxkj334rzv?version=7 ; .../vxkj334rzv/files?folder_id=root&version=7 ; .../vxkj334rzv/folders/7 ; https://data.mendeley.com/datasets/vxkj334rzv/7 | metadata |
| M-S2 | Mendeley Data `x3vhp8t6hg` v7 (Subset2) | https://data.mendeley.com/public-api/datasets/x3vhp8t6hg?version=7 ; .../x3vhp8t6hg/files?folder_id=root&version=7 ; .../x3vhp8t6hg/folders/7 ; https://data.mendeley.com/datasets/x3vhp8t6hg/7 | metadata |
| M-S3 | Mendeley Data `j8d8pfkvj2` v7 (Subset3) | https://data.mendeley.com/public-api/datasets/j8d8pfkvj2?version=7 ; .../j8d8pfkvj2/files?folder_id=root&version=7 ; .../j8d8pfkvj2/folders/7 ; https://data.mendeley.com/datasets/j8d8pfkvj2/7 | metadata |
| M-HIST | Metadata and file listings of every earlier version (v1-v6 / v1-v7) | `https://data.mendeley.com/public-api/datasets/<id>?version=<v>` and `.../<id>/files?folder_id=root&version=<v>` | metadata |
| DC | DataCite DOI records | https://api.datacite.org/dois/10.17632/ztmf3m7h5x.6 (and .../vxkj334rzv.7, .../x3vhp8t6hg.7, .../j8d8pfkvj2.7, .../ztmf3m7h5x.2, .../vxkj334rzv.2) | metadata |
| D-VL | Older `Description_v1.pdf` for the varying-load data (942,199 B, SHA-256 011f25ab...cc962d81). Present only in versions 2-4 of ztmf3m7h5x. | https://data.mendeley.com/public-files/datasets/ztmf3m7h5x/files/307fc169-402f-4baa-955d-17c998e5f67b/file_downloaded | full_text (15 pp.) |
| D-VS | Older `Description_v1.pdf` for the varying-speed data (1,700,019 B, SHA-256 e28b227e...dda76c25e). Identical copies in vxkj334rzv v2-v4, x3vhp8t6hg v2-v3 and j8d8pfkvj2 v2-v3. | https://data.mendeley.com/public-files/datasets/vxkj334rzv/files/6d017841-c794-4b7c-a21e-3465623fabca/file_downloaded | full_text (14 pp.) |
| NI9211 / NI9210 / NI9775 | NI product pages | https://www.ni.com/en-us/shop/model/ni-9211.html ; https://www.ni.com/en-us/shop/model/ni-9210.html ; https://www.ni.com/en-us/shop/model/ni-9775.html | full page (title strings grepped verbatim) |
| HIOKI | Hioki CT6700 product page | https://www.hioki.com/sg-en/products/current-probes/wide-band/id_6079 | full page (fetched with curl; WebFetch got 403) |
| IECON | Kim, Jung, Lim, Park, IECON 2022, doi:10.1109/IECON49645.2022.9969003 (related article cited by P) | https://api.crossref.org/works/10.1109/IECON49645.2022.9969003 | metadata only (not read) |
| GH | GitHub account linked from M-S1..3 `related_links` | https://api.github.com/users/wonho1456 ; https://api.github.com/users/wonho1456/repos | metadata. **0 public repositories**, so no loader code exists. |
| LOCAL | Local copies of the three varying-load zips at `D:\bahrain-data\raw\kaist\` (downloaded separately from the M-VL `download_url`s). SHA-256 recomputed on 2026-11-07 and identical to the M-VL values. Read only: zip central directories, MAT headers and structs, TDMS metadata, and the first 10 s of 3 TDMS files. Nothing was extracted or executed. | file paths as shown | data files (metadata level) |

The following were not accessible:

- PCB 352C34 product page (https://www.pcb.com/products?m=352c34, HTTP 403), so the accelerometer specifications are **not** verified.
- PMC HTML PDF link (bot interstitial) and the Europe PMC PDF render (403). The PDF was obtained from the PMC Open Access S3 bucket instead.
- The IEEE Xplore full text of IECON 2022 was not attempted (metadata only).
- The varying-speed zips (21.4 GB) were neither downloaded nor inspected.

Corrections and retractions: the Crossref `updates` filter returned 0 records [CR]. The PMC OA metadata has `"is_retracted": false` [PMCJ]. The PubMed record shows no CommentsCorrections entries (https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=36969976&retmode=xml).

Paper metadata: received 17 Feb 2023, accepted 2 Mar 2023, available online 9 Mar 2023 [P p.1]. Volume 48 (June 2023), article 109049 [CR]. Open access under CC BY 4.0 [P p.1 footer; CR `license` (vor)]. Crossref lists the four Mendeley datasets as `is-supplemented-by` [CR `relation`]. The Mendeley records, in turn, have an empty `articles` list and link only to the journal home page https://www.sciencedirect.com/journal/data-in-brief [M-VL `description`/`method`; M-S1..3 `description`].

---

## 2. Mendeley Data records: licence, version and files

### 2.1 Records

| Record | Title (Mendeley `name`) | Version used (latest) | Version DOI | Published (API `publish_date`) | Licence | Folders |
|---|---|---|---|---|---|---|
| ztmf3m7h5x | Vibration, Acoustic, Temperature, and Motor Current Dataset of Rotating Machine Under Varying Load Conditions for Fault Diagnosis | 6 (versions 1-6 exist; v1 2022-08-15T18:16:12Z) | 10.17632/ztmf3m7h5x.6 | 2023-02-08T10:58:38.145Z | CC BY 4.0, "Creative Commons Attribution 4.0 International", http://creativecommons.org/licenses/by/4.0 | none (`folders/6` returns `[]`) |
| vxkj334rzv | Vibration and Motor Current Dataset of Rolling Element Bearing Under Varying Speed Conditions for Fault Diagnosis: Subset1 | 7 (v1 2022-08-15T18:22:42Z) | 10.17632/vxkj334rzv.7 | 2023-02-08T10:51:08.888Z | CC BY 4.0 | none |
| x3vhp8t6hg | ... : Subset2 | 7 (v1 2022-08-15T18:24:37Z) | 10.17632/x3vhp8t6hg.7 | 2023-02-09T13:51:46.805Z | CC BY 4.0 | none |
| j8d8pfkvj2 | ... : Subset3 | 7 (v1 2022-08-15T18:21:40Z) | 10.17632/j8d8pfkvj2.7 | 2023-02-09T13:51:42.526Z | CC BY 4.0 | none |

Sources: [M-VL], [M-S1], [M-S2], [M-S3], fields `version`, `versions`, `publish_date`, `data_licence`, `doi`. The landing pages show the same version, date, DOI and "CC BY 4.0".

- **Contributors.** The Mendeley record lists five contributors: Wonho Jung, Seong-Hu Kim, SungHyun Yun, Jaewoong Bae and Yong-Hwa Park (KAIST; Bae is listed as "Hyundai Motor Group" in Subset2/3) [M-VL, M-S1..3 `contributors`]. The DataCite records list only **"Wonho Jung"** as creator for all four DOIs, with rights "Creative Commons Attribution 4.0 International" (legalcode URL) [DC].
- **DOI resolution.** Each version DOI resolves (HTTP 302) to `https://data.mendeley.com/datasets/<id>/<v>` [DC].
- **Related links.** Subsets 1-3 list the related link `https://github.com/wonho1456?tab=repositories` [M-S1..3 `related_links`]. That account has 0 public repositories [GH].

### 2.2 Files (published SHA-256)

| Record (version) | File | Mendeley file id | Size (bytes) | Published SHA-256 | Uploaded (`created_date`) |
|---|---|---|---|---|---|
| ztmf3m7h5x (v6) | `acoustic.zip` | 99f03ffd-04f9-4676-932a-4312284cbc18 | 47,205,730 | 5dd1371ccec00729498e2d151df13593f6400fdced8895481ff6a8a945a5962f | 2022-08-15T06:42:55.562Z |
| ztmf3m7h5x (v6) | `current,temp.zip` | 4fe7c7e8-9a77-4bef-b359-d762b6a3a044 | 1,547,790,068 | 7caa22152ff1fd673a6a3a9614f95fabd2890c6aea0860b40a1f5b27eabb59d6 | 2022-08-15T06:50:27.409Z |
| ztmf3m7h5x (v6) | `vibration.zip` | ee98c5d9-1052-4448-84b2-ed57711b658d | 2,659,778,162 | df73fa80371a2ad3c983825044447b7772fcefd1db2ac409b2b298b533e4659f | 2022-08-15T06:56:52.697Z |
| vxkj334rzv (v7) | `part1.zip` | 3d93576c-d623-41fd-aecf-9308c69dbace | 10,350,759,860 | e0d6089fd132b4027866f0240232850503a3a788c6be5c0b7f2d52d535a42ba7 | 2022-08-15T09:52:17.647Z |
| x3vhp8t6hg (v7) | `part2.zip` | 81087668-a525-412d-892d-5d6bf1165da3 | 5,529,338,644 | 496b8031d22778b58cd66a35f9c1d7bf14b86940ebd6f73cebc94f4c88aded09 | 2022-08-15T09:45:01.381Z |
| j8d8pfkvj2 (v7) | `part3.zip` | 4bd6fec3-69af-4ab0-9829-c1438ef95ef4 | 5,536,452,993 | 8b0f95eaccaa8f0c2ed73fb3ce19e319234cbcb2b8b3470a091ea4eb9394b22a | 2022-08-15T09:44:56.625Z |

Sources: [M-VL], [M-S1], [M-S2], [M-S3] `files?folder_id=root&version=...`, fields `filename`, `id`, `size`, `content_details.sha256_hash`, `content_details.created_date`. Download URLs have the form `https://data.mendeley.com/public-files/datasets/<id>/files/<file id>/file_downloaded`.

Totals: varying-load 4,254,773,960 B; varying-speed 21,416,551,497 B (my arithmetic).

**Version history** [M-HIST]:

- The data zips have the **same SHA-256 in every version** since v1. Later versions changed only the descriptions and a documentation PDF.
- A `Description_v1.pdf` was present in ztmf3m7h5x v2-v4 and in vxkj334rzv v2-v4, x3vhp8t6hg v2-v3 and j8d8pfkvj2 v2-v3. It was removed afterwards; these are [D-VL] and [D-VS].
- Neither the records nor the paper say **which varying-speed files are inside part1/part2/part3.zip**. Only the subset split "because of storage limitations" is stated [M-S1..3 `description`].

The local copies of the three varying-load zips match the published SHA-256 exactly (recomputed 2026-11-07) [LOCAL].

---

## 3. Test bed (documented)

| Item | Documented value | Quote and location |
|---|---|---|
| Layout | Motor, torque meter, gearbox, bearing housing A, bearing housing B, rotors, hysteresis brake | "The rotating machine testbed consists of three-phase induction motor, torque meter, gearbox, bearing housing A, bearing housing B, rotors and hysteresis brake as shown in Fig. 5." [P p.14 §3.1]. Fig. 5 shows, from left: brake, bearing housing B, rotors (mass wheel), bearing housing A, gearbox, torque meter, motor (3 HP); current probes labelled R/S/T at the motor [P Fig. 5 p.14, viewed]. |
| Motor | Siemens, 3-phase induction, 4-pole, 3 HP, 380 V, 60 Hz, rated 1770 rpm | "The three-phase induction motor manufactured by SIEMENS is four-pole AC motor with 3 horse-power (HP). It is driven at 380 V, 60 Hz, at a rated speed of 1770 rpm." [P p.14 §3.1] |
| Gearbox and speed (varying-load part) | ×2.07, up to 3663 rpm; operated at **3010 rpm** (constant) | "The gearbox increases the rotating speed by 2.07 times, up to 3663 rpm. To avoid signal overlap with the driving frequency of 60 Hz, this dataset was operated at 3010 rpm." [P p.14 §3.1]. Also "The main motor rotates at a rated rotating speed of 3010 RPM." [P p.4 §2]. Table 2 lists 3010 RPM for every row [P p.17]. The bearing frequencies use fs = 50.17 Hz [P p.15]. |
| Load | Hysteresis brake AHB-3A (Valid Magnetic Ltd.), air-cooled; torque meter M425 (Datum Electronics); **0, 2, 4 Nm** | "A load was applied to the rotating machine using a hysteresis brake (AHB-3A) manufactured by Valid Magnetic Ltd., and the load was measured with a torque meter (M425) manufactured by Datum Electronics. The simulated loads in this dataset are 0 Nm, 2 Nm, and 4 Nm." [P p.14 §3.1]. "The load conditions are controlled by hysteresis brake with air cooling method." [P p.4 §2]. **Not documented:** whether 0/2/4 Nm is the brake (output-side) torque or the torque-meter reading. Fig. 5 places the torque meter between motor and gearbox. |
| Bearing (varying load) | NSK 6205 DDU; d = 7.90 mm, D = 38.5 mm, θ = 0°, N = 9; FTF 19.94 Hz, BPFI 272.07 Hz, BPFO 179.43 Hz, BSF 234.19 Hz at fs = 50.17 Hz | [P p.15 §3.2, Table 1] |
| Bearing faults (varying load) | Inner and outer race "crack sizes" **0.3, 1.0, 3.0 mm**; faulty bearing in **housing A** | "...the bearing faults, including inner race fault and outer race fault were simulated according to the crack sizes (0.3 mm, 1.0 mm, and 3.0 mm) as shown in Fig. 6. The corresponding fault-seeded bearing was installed in the bearing housing A." [P p.15 §3.2]. Fig. 6 caption: "Bearing by crack size: (a) inner race 0.3 mm, ... (f) outer race 3.0 mm" [P p.15]. **The method of making the cracks is not stated** for this part (no EDM, drilling or cutting description). The photos show a single transverse notch on the race [P Fig. 6, viewed]. |
| Misalignment | Parallel misalignment of the shaft at housing A: 0.1, 0.3, 0.5 mm | "Shaft fault is a parallel misalignment that moves the shaft in bearing housing A as shown in Fig. 7. The movements consist of 0.1 mm, 0.3 mm, and 0.5 mm." [P p.15]. Fig. 7 shows a digital indicator reading 0.00 and 0.30 [P Fig. 7 p.16, viewed]. |
| Unbalance | Added mass on the 4th rotor disk (closest to housing A): 583, 1169, 1751, 2239, 3318 mg | "Rotor faults are seeded by adding mass to the fourth rotor disk ... The unbalanced disk is the closest disk to bearing housing A. This dataset consists of the unbalanced masses: 583 milligram (mg), 1169 mg, 1751 mg, 2239 mg, and 3318 mg." [P p.15]. **Mounting radius not stated**, so the unbalance in g·mm is unknown. |
| Bearing (varying speed) | "type 6205 steel NSK ball bearing"; normal, inner, outer and ball faults made by "spalling surface ... using diamond tips"; **defect sizes not stated** | [P pp.15-16 §3.2]; Fig. 9 [P p.18]; the same wording appears in [D-VS p.12]. |
| Speed (varying speed) | **680-2460 rpm**, "randomly varying", no load; set by adjusting the motor frequency; constant-speed reference recordings at 3010 rpm | Abstract "(680 RPM to 2460 RPM)" [P p.1]; "Second dataset was acquired from the testbed under randomly varying rotating speed condition without load." [P p.2 Spec. Table]; "The varying speed conditions was simulated by adjusting the frequency of the motor as shown in Fig. 5." [P p.16]; Table 3 [P p.17]. "(680 RPM and 2460 RPM)" appears on p.8 and p.9 (wording inconsistency). |

Two points about speed are ambiguous:

- **Varying-speed part.** The rpm files are described as "rotating speed of main motor" [P pp.9-10]. Yet 3010 rpm is reachable only after the ×2.07 gearbox (the motor is rated 1770 rpm). The paper does **not** say whether 680-2460 rpm is the motor speed or the gearbox-output (bearing-shaft) speed. Inference: the Fig. 5 "RPM monitoring" display reads 3009 at the operating point, which suggests the shaft side.
- **Varying-load part.** The supply frequency is not stated. Observed: the current fundamental in the varying-load files is about **48.5 Hz** (FFT of the first 10 s, 0.1 Hz resolution, `0Nm_Normal`, `4Nm_Normal` and `0Nm_BPFO_30` [LOCAL]). This is consistent with a variable-frequency drive at about 48.5 Hz rather than 60 Hz mains (inference).

---

## 4. Sensors and acquisition (documented)

### 4.1 Varying-load part (ztmf3m7h5x)

| Modality | Sensor and position | DAQ (as documented) | fs (documented) | Duration (documented) | Location |
|---|---|---|---|---|---|
| Vibration | 4 × PCB352C34 ICP accelerometers; x and y at housings A and B; "simultaneously" | Siemens SCADAS Mobile 5PM50 | 25.6 kHz | 120 s normal, 60 s faulty | [P p.4 §2; p.2 Spec. Table; Table 2 p.17] |
| Acoustic | 1 × PCB378B02 microphone near housing A (ISO 8528-10); **0 Nm only** | Siemens SCADAS Mobile 5PM50 | 51.2 kHz | 60 s (Table 2) | [P p.4 §2; p.14 §3.1; Table 2 p.17] |
| Temperature | 2 × K-type thermocouples, one per bearing housing | "NI9211" (§2), but "NI 9775" in the Specifications Table | 25.6 kHz | as vibration | [P p.4 §2; p.2] |
| Motor current | 3 × Hioki CT6700 on U, V and W phases | "NI9775" (§2), but "NI 9211" in the Specifications Table | 25.6 kHz | as vibration | [P p.4 §2; p.2; p.14 §3.1] |

Quotes:

- §2: "Siemens SCADAS Mobile 5PM50 was used for collecting vibration and acoustic data. NI9211, and NI9775 modules were used for collecting temperature, and driving current data, respectively. Vibration, temperature, driving current data were collected at a sampling frequency of 25.6 kHz. This dataset was collected for 120 seconds in normal state, and for 60 seconds in faulty state. Lastly, acoustic data were collected with a sampling frequency of 51.2 kHz and only acquire bearing fault data under no-load conditions to avoid the noise from air-cooled brakes." [P p.4 §2]
- Specifications Table: "Temperature, and driving current data are collected from thermocouples and CT sensors by NI 9775 and NI 9211, respectively." [P p.2]. This contradicts §2. The NI pages show that NI 9211 is a "4-Channel, 14 S/s, ±80 mV C Series Temperature Input Module" [NI9211] and NI 9775 a "±10 V, Up to 20 MS/s/ch, 14-Bit, 4-Channel C Series Digitizer Module" [NI9775]. The §2 mapping is therefore the plausible one.
- The older description says the same thing in both places, including the swap in its Specifications Table [D-VL p.2, p.3]. Its Specifications Table also says acoustic was sampled at "25.6 kHz and 50 kHz" [D-VL p.2], whereas its body text and the paper say 51.2 kHz.
- Sensor model typo: "PCB352C34" [P p.2, p.4] versus "PCB35234" [P p.14 §3.1].
- Hioki CT6700 (vendor page): "Frequency bandwidth DC to 50 MHz (-3 dB)", "Continuous allowable input 5 A rms", "Max. allowable peak input ±7.5 A peak (non-continuous)", "Output rate 1 V/A" [HIOKI].

### 4.2 Varying-speed part (vxkj334rzv / x3vhp8t6hg / j8d8pfkvj2)

| Modality | Sensor | DAQ | fs | Duration | Location |
|---|---|---|---|---|---|
| Vibration | 4 × PCB352C34, x and y at housings A and B | Siemens SCADAS Mobile 5PM50 | 25.6 kHz | 600 s per state at constant 3010 rpm (housing A); 2,100 s per state varying, as 7 files × 300 s (housing B) | [P p.9; Table 3 p.17] |
| Motor current | 3 × Hioki CT6700 (R, S, T phases) | NI9775 | **100 kHz** | varying speed only: 7 × 300 s per state | [P p.9; Table 3 p.17] |
| Speed | 1 tachometer, Autonics FD-620-10 | **not stated** | **not stated** | 7 × 300 s per state | [P p.2 Spec. Table; p.9] |

- "Vibration data were acquired by a Siemens SCADAS Mobile 5PM50 with sampling frequency of 25.6 kHz, and current data were acquired by NI9775 with sampling frequency of 100 kHz. This dataset was collected for 600 seconds at constant speed, and for 2,100 seconds at varying speed conditions (680 RPM and 2460 RPM)." [P p.9]
- The older description calls the tachometer "one laser-based tachometer" and says "The speed information can extract from not only motor current data but also tachometer." [D-VS p.1]. It also says "Vibration and motor current data are collected from SIEMENS DAQ and NI DAQ for 2,100 seconds." [D-VS p.2] and "The dataset at constant speed are one file for each state. The dataset at varying speed are seven files for each state." [D-VS p.3].
- No current data are listed for the constant-speed (3010 rpm) recordings of this part [P p.9 file list; Table 3 p.17].

### 4.3 Synchronisation: everything the documents say

Exact quotes:

1. "Vibration data were measured using four accelerometers (PCB352C34) at two bearing housings (A, B) in the x-direction and y-direction, simultaneously." [P p.4 §2]. This covers only the four accelerometers.
2. "...eliminating the effect of varying speed condition such as order tracking are conducted, however, it needs to collect synchronized speed data with vibration [5]." [P p.3, Value of the Data]
3. "Synchronized speed data and vibration data under constant speed conditions are also provided [2]." [P p.3, Value of the Data]
4. "To support more details in this dataset, synchronized speed data are also provided." [P p.9]. The same sentence appears in [D-VS p.3]. [D-VS p.3, Value of the data] adds: "synchronized speed data, and vibration data under constant speed conditions are also included".
5. "Temperature and motor current data are collected from NI DAQ in the same way as vibration and acoustic." [D-VL p.2 Spec. Table]. This is ambiguous and reads as "same durations", not as a synchronisation statement.

**Not documented** (paper, Mendeley records and both older description PDFs):

- whether the SCADAS and NI systems shared a clock, trigger or sync signal;
- the time offset between vibration and current files;
- which DAQ recorded the tachometer, and against which stream the speed is "synchronized";
- the meaning and units of the "Time Stamp" columns (relative or absolute; seconds or other);
- the time zone;
- whether the acoustic recordings were simultaneous with the vibration recordings;
- how temperature, sampled by a slow thermocouple module, ends up on a 25.6 kHz time base.

What the files show about all this is in Section 8.

---

## 5. Independent experimental units (what is and is not documented)

**Documented:**

- Varying load: one fault-seeded bearing "was installed in the bearing housing A" ("The corresponding fault-seeded bearing", singular) [P p.15 §3.2]. Fig. 6 shows **one photograph per (race, crack size)**: six bearings in total [P p.15]. Table 2 gives one row per fault and severity with "Load (Nm) 0, 2, 4" [P p.17]. The file lists give **exactly one file per (load, condition, severity)**: 45 vibration MAT, 45 TDMS and 5 acoustic MAT files [P pp.4-8; M-VL `description`].
- Varying speed: Fig. 9 shows one bearing per state (normal, inner, outer, ball) [P p.18]. Table 3 gives fault location "Bearing housing A" for the constant-speed runs and "Bearing housing B" for the varying-speed runs [P p.17]. The file list says "Bearing with inner fault is installed in bearing housing B" (and likewise for outer and ball) for the varying-speed files, and, for the constant-speed files, "(47) vibration_inner/outer/ball_constant.csv ... Bearing with ball fault is installed in bearing housing A." [P p.9]. Per state there is 1 constant-speed file (600 s) and 7 varying-speed files (300 s each) [P p.9; D-VS p.3].

**Not documented:**

- the number of physical bearings per class or severity;
- whether the same faulty bearing was reused (left mounted) across 0, 2 and 4 Nm, or re-mounted;
- which bearing (or how many healthy bearings) sat in housing A during the normal, unbalance and misalignment runs, and what was in housing B;
- whether the acoustic runs used the same specimens;
- whether the varying-speed specimens were moved from housing A (constant speed) to housing B (varying speed);
- whether the 7 × 300 s files form one continuous 2,100 s run or separate runs;
- defect geometry for the varying-speed faults;
- any repeated runs.

**Observed in file metadata (varying load) [LOCAL], with inference:**

- The TDMS start times give the recording order. Each bearing-fault severity was recorded at 0 → 2 → 4 Nm in one block of about 7-18 min:
  - inner 3.0 mm: 10:40-10:48 UTC on 2021-06-28;
  - inner "1 mm": 11:02-11:17;
  - inner "0.3 mm": 11:29-11:41;
  - outer 0.3 mm: 07:48-07:56 on 2021-06-30;
  - outer 1.0 mm: 08:26-08:45;
  - outer 3.0 mm: 09:02-09:10.
- The normal, unbalance and misalignment runs were all recorded on 2021-06-25 between 06:59 and 09:34 UTC.
- The acoustic runs were recorded on 2021-07-05 [LOCAL acoustic MAT `absolute_time`].
- **Inference:** one specimen per (race, severity), kept mounted across the three loads. One healthy-bearing setup for the normal, unbalance and misalignment runs. Specimens re-mounted for the acoustic session.

**Consequence for bearing-grouped cross-fitting (inference):** on KAIST, a "bearing group" can only be a (fault type, severity) specimen. There are three inner-race and three outer-race groups, and probably one healthy bearing shared by the normal, unbalance and misalignment classes. A leave-one-bearing-out split is impossible for the healthy class and confounds severity with specimen for the faulty classes. The varying-speed part has one specimen per class, so no bearing grouping is possible; only temporal blocks (7 files) are available.

---

## 6. File naming scheme and units

### 6.1 Varying load, `aaaaNm_bbbb_cccc.mat` / `.tdms` [M-VL `description`; P pp.4-8]

- Mendeley: "aaaaNm_bbbb_cccc.mat : This file includes vibration data of the condition of "bbbb" with "cccc" of severity and "aaaa" load condition." The acoustic `.mat` entry uses the same wording. For the TDMS files: "aaaaNm_bbbb_cccc.tdms : This file includes temperature and motor current data of the condition of "bbbb" with "cccc" of severity and "aaaa" load condition." [M-VL `description`]

| Field | Meaning (documented) | Values used (from the file lists, P pp.4-8) |
|---|---|---|
| `aaaa` | load (Nm) | `0`, `2`, `4` |
| `bbbb` | condition | `Normal`, `BPFI` (inner race), `BPFO` (outer race), `Misalign` (parallel misalignment), `Unbalance` (rotor unbalance) |
| `cccc` | severity | BPFI/BPFO: `03`, `10`, `30` = 0.3, 1.0, 3.0 mm; Misalign: `01`, `03`, `05` = 0.1, 0.3, 0.5 mm; Unbalance: `0583mg`, `1169mg`, `1751mg`, `2239mg`, `3318mg`; Normal: no field (`0Nm_Normal`) |

- Example names: `0Nm_Normal.mat`, `0Nm_BPFI_03.mat`, `0Nm_Misalign_01.mat`, `0Nm_Unbalance_0583mg.tdms`. The acoustic set has only `0Nm_Normal`, `0Nm_BPFI_03`, `0Nm_BPFI_10`, `0Nm_BPFO_03` and `0Nm_BPFO_10` [P p.6].
- Documented columns and units:
  - Vibration: 'Time Stamp', 'x_direction_housing_A', 'y_direction_housing_A', 'x_direction_housing_B', 'y_direction_housing_B'; unit g (1 g = 9.80665 m/s²) [P p.4].
  - Acoustic: 'Time Stamp', 'values'; unit Pa [P p.4].
  - TDMS: 'Time Stamp', 'Temperature_housing_A', 'Temperature_housing_B', 'U-phase', 'V-phase', 'W-phase'; units °C and A [P p.6; M-VL].
- Observed [LOCAL]:
  - The zip contents match these names except five files spelled **`2Nm_Unbalalnce_0583mg.mat` ... `2Nm_Unbalalnce_3318mg.mat`** in `vibration.zip`.
  - **No literal "Time Stamp" or named columns** exist. See §8.2.

### 6.2 Varying speed [M-S1..3 `description`; P pp.9-10]

- `vibration_aaaa_bbbb.csv`: "This file is "bbbb"-th vibration data includes rotating speed data of the condition of "aaaa"."
- `current_aaaa_bbbb.csv`: "This file is "bbbb"-th motor current data ...".
- `rpm_aaaa_bbbb.csv`: "This file is "bbbb"-th speed data ..." [M-S1..3].

The fields are:

- `aaaa` ∈ {`normal`, `inner`, `outer`, `ball`};
- `bbbb` ∈ {`0` ... `6`} (300 s each);
- plus `vibration_<state>_constant.csv` (600 s, 3010 rpm) [P p.9].

Columns and units:

- Vibration: 'Time Stamp' plus 4 axes, in g.
- Current: "five columns namely 'Time Stamp', 'R_phase', 'S_phase', and 'T_phase'", in A. Only four names are listed for "five columns" [M-S1..3; P p.9].
- Speed: 'Time Stamp', 'speed', in RPM. The Mendeley text says "The unit of the acoustic is revolutions per minute (RPM)" (a copy-paste slip) [M-S1..3].

The Mendeley varying-speed description lists only "healthy bearing, bearings with inner race faults, and bearings with outer race faults" and omits the ball fault that the paper describes [M-S1..3 vs P p.3, p.9]. None of this was verified at file level, because the zips were not inspected.

---

## 7. Inconsistencies found in the documentation

1. **Module mapping.** The Specifications Table maps NI 9775 to temperature and NI 9211 to current [P p.2; same in D-VL p.2]. §2 says NI9211 is temperature and NI9775 is current [P p.4]. The files say **NI 9210** for temperature and NI 9775 for current [LOCAL].
2. **Accelerometer model.** "PCB352C34" [P p.2, p.4, p.9] versus "PCB35234" [P p.14].
3. **Durations.** Normal 120 s and faulty 60 s are documented [P p.4; Table 2 p.17]. The files show misalignment and unbalance at 120 s and `0Nm_Normal` at 300 s [LOCAL].
4. **Temperature rate.** Temperature is "collected at a sampling frequency of 25.6 kHz" [P p.4]. The thermocouple modules are 14 S/s devices [NI9210, NI9211]. The files show held values changing about 4.8 times per second [LOCAL].
5. **Acoustic sampling rate.** "25.6 kHz and 50 kHz" in [D-VL p.2] versus 51.2 kHz in [P p.4], [D-VL p.3] and the files [LOCAL].
6. **Meaning of "3010 RPM".** "The main motor rotates at a rated rotating speed of 3010 RPM" [P p.4] versus motor rated 1770 rpm with a ×2.07 gearbox [P p.14]. Varying-speed rpm files are "rotating speed of main motor" [P pp.9-10], and the reference point (motor or shaft) is not defined.
7. **Speed range wording.** "(680 RPM and 2460 RPM)" [P p.8, p.9] versus "680 RPM to 2460 RPM" [P p.1, p.3].
8. **Current file columns.** "five columns" but four names [P p.9; M-S1..3].
9. **Missing ball fault.** The Mendeley varying-speed description omits the ball fault [M-S1..3].
10. **Bearing housing for constant-speed files.** "Bearing with ball fault is installed in bearing housing A" is attached to the combined inner/outer/ball constant-speed entry [P p.9 item (47)]. The older description repeats it for each of the inner, outer and ball constant files [D-VS p.4].
11. **Phase labels.** U/V/W in the varying-load part [P p.6] versus R/S/T in the varying-speed part [P p.9]. Fig. 5 labels the probes R/S/T [P p.14]. The files carry neither label (`Mod2/ai0, ai2, ai3`) [LOCAL].
12. **Title mismatch.** The Mendeley varying-load `method` field cites the article title "...Under Varying Load Conditions..." while `description` cites "...Under Varying Operating Conditions..." (the published title) [M-VL].
13. **File name typo.** `Unbalalnce` appears in 5 vibration file names [LOCAL].
14. **Creators.** DataCite lists only Wonho Jung as creator, while the Mendeley record and the paper list five authors [DC; M-VL; P p.1].

---

## 8. File-level verification of the varying-load data (local copies) [LOCAL]

### 8.1 Method

The three local zips were checked by SHA-256 against [M-VL] (all identical). They were read without extraction, using Python 3.13 in isolated mode:

- `zipfile` for the central directory;
- `scipy.io.loadmat` for the MAT structs;
- a small read-only TDMS metadata parser written for this check (npTDMS is not installed);
- raw values read only for the first 10 s of three TDMS files.

The per-condition table is in `E:\bahrain\manifests\kaist_documentation.json` (`file_level_verification_varying_load.per_condition`).

### 8.2 Container structure (no "Time Stamp" column)

**Vibration and acoustic `.mat` files**

- Format: MATLAB 5.0 MAT-files, each holding a single struct `Signal` exported by Siemens Simcenter Test.Lab (`quantity.info` = "Data saved by Test.Lab in MKS").
- `Signal.x_values` holds `start_value` (a few µs), `increment` (3.90625e-05 s for vibration, i.e. 25,600 Hz; 1.953125e-05 s for acoustic, i.e. 51,200 Hz) and `number_of_values`.
- `Signal.y_values.values` is an N×4 float64 array in g for vibration (channel names `3:Point1` ... `6:Point4`) and an N×1 array in Pa for acoustic (`3:Point1`).
- `Signal.function_record.TL_export_properties_annotation` holds `run_name`, `absolute_time` (for example '2021-06-28 11:32:36 ms 799.212') and `channel_group` ('Vibration' or 'Acoustic').
- `creation_time` is local time, 9 h ahead of `absolute_time`. Inference: `absolute_time` is UTC, since Korea is UTC+9.

**Current and temperature `.tdms` files**

- Written by NI FlexLogger 2021 R1.1. Root properties include `name` (for example 'LogFile_0Nm_Inner_1mm'), `Date Created` and `RunNumber`.
- Group `'Log'` has channels:
  - `cDAQ9185-1F486B5Mod1/ai0`, `ai1`: thermocouple, K type, °C, device "NI 9210 (miniTC)";
  - `cDAQ9185-1F486B5Mod2/ai0`, `ai2`, `ai3`: current, A, device "NI 9775", a voltage channel scaled at 1 V/A (`NI_SensorScale~ScaleType` = InverseLinear, `NI_SensorSensitivity` = 1.0, range ±10).
- Per-channel `wf_start_time` is UTC, `wf_increment` = 3.905e-05 s and `wf_start_offset` = 0.
- Hence the time axis is implicit in both formats: start time plus k·increment. The documented column names do not appear in the files.
- **Inference:** the documented column order suggests that MAT channels Point1-4 map to x_A, y_A, x_B, y_B, and TDMS ai0/ai2/ai3 to U/V/W. This mapping is not stated anywhere. As supporting evidence, in the bearing-fault files the RMS is highest on Point1-2, which fits the faulty bearing being in housing A.

### 8.3 Sampling and duration (all 45 + 45 + 5 files)

| Group | Vibration (MAT) | Current/temperature (TDMS) | Documented |
|---|---|---|---|
| BPFI and BPFO (18 conditions) | 1,536,000 samples at 25,600 Hz = **60 s** | 1,536,492 samples at 3.905e-05 s ≈ **60 s** | 60 s ✔ |
| Misalign and Unbalance (24) | 3,072,000 = **120 s** | 3,072,983 ≈ **120 s** | 60 s ✗ |
| Normal 2 Nm and 4 Nm | 3,072,000 = 120 s | 3,072,983 ≈ 120 s | 120 s ✔ |
| Normal 0 Nm | 7,680,000 = **300 s** | 7,682,458 ≈ **300 s** | 120 s ✗ |
| Acoustic (5 files, 0 Nm) | 3,072,000 at 51,200 Hz = 60 s | n/a | 60 s ✔ |

TDMS rate: 1/3.905e-05 ≈ **25,608.2 Hz**, not 25,600 Hz. Over 60 s the current stream has 492 more samples than the vibration stream, so pairing at sample level needs resampling.

### 8.4 Clocks and concurrency of vibration and current

For each condition I computed: vibration `absolute_time` − TDMS `wf_start_time`.

- **Daily offsets.** 203.03 s on 2021-06-25 (27 conditions), 197.90 s on 2021-06-28 (9), 206.58 s on 2021-06-30 (6 concurrent ones).
- **Spread.** After removing the daily median, 34 of 42 pairs fall within ±0.25 s and 40 within ±1 s. The extremes are +2.76 s (`4Nm_Unbalance_1169mg`) and −1.76 s (`0Nm_Normal`).
- **Why this is a clock offset.** The gaps between consecutive runs varied from about 174 s to 507 s, yet the vibration-minus-current offset stayed at 203.0 ± 0.3 s. That rules out the vibration file having been recorded together with a *different* current run.
- **Inference:** the two acquisition hosts ran on clocks about 3.3-3.4 min apart, and the paired recordings were started nearly together. The pairs overlap for almost their whole length but are **not sample-synchronised**. The start alignment is uncertain to roughly 0.1-3 s from metadata alone.
- **Outer race 0.3 mm (0, 2, 4 Nm): not concurrent.** The vibration runs start 1,911-1,916 s (about 32 min) *before* the current runs, after the clock correction. No published current file is concurrent with these vibration files.
- **Inner race at 0 Nm.** Vibration `0Nm_BPFI_03.mat` (run name '..._0Nm_Inner_0.3mm') is concurrent with **`0Nm_BPFI_10.tdms`** (residual −0.10 s). Vibration `0Nm_BPFI_10.mat` (run '210628_0Nm_Inner_1mm') is concurrent with **`0Nm_BPFI_03.tdms`** (residual −0.65 s). See §8.5.
- **Acoustic.** All five acoustic files were recorded on **2021-07-05** (`absolute_time` 14:48-16:26 UTC) with run names ending in "_5cm". They are not concurrent with any vibration or current file. The meaning of "5cm" (perhaps microphone distance) is undocumented.

### 8.5 Probable label swap in the 0 Nm inner-race TDMS files

| Published file | Internal FlexLogger `name` | Start (UTC, NI clock) | Recording block in time | Concurrent vibration file |
|---|---|---|---|---|
| `0Nm_BPFI_03.tdms` | 'LogFile_0Nm_Inner_1mm' | 2021-06-28 11:02:43 | "1 mm" block (2 Nm and 4 Nm at 1 mm: 11:13, 11:16) | `0Nm_BPFI_10.mat` (run '210628_0Nm_Inner_1mm') |
| `0Nm_BPFI_10.tdms` | 'LogFile_0Nm_Inner_03mm' | 2021-06-28 11:29:19 | "0.3 mm" block (2 Nm and 4 Nm at 0.3 mm: 11:36, 11:39) | `0Nm_BPFI_03.mat` (run '..._0Nm_Inner_0.3mm') |

**Inference:** the two current/temperature files carry swapped published names. The vibration names agree with their run names, and the vibration RMS profiles are consistent across 0, 2 and 4 Nm within each severity. Before using KAIST current at 0 Nm, either swap these two labels or confirm them from current spectra. The 2 Nm and 4 Nm BPFI TDMS files agree with their internal names.

### 8.6 Outer-race current has a single phase

In all nine `*_BPFO_*.tdms` files, `Mod2/ai2` and `Mod2/ai3` have zero values. Only `Mod2/ai0` holds current (1,536,492 samples). This explains why these files are about 36.9 MB against about 61.5 MB for BPFI. Every other TDMS file has three current channels with data.

**Consequence:** a three-phase current model would see a class-dependent missing-channel pattern, which leaks the label. Use a single phase (`ai0`) throughout, or exclude BPFO.

### 8.7 Other observations

- Temperature channels have the same sample count as current, but their values change only about 4.8 times per second (49 distinct values in 10 s): a slow thermocouple signal held on the fast time base.
- Current in the first 10 s: about 2.2 A rms at 0 Nm and 2.7 A rms at 4 Nm (normal), with peaks up to 5.3 A, inside the CT6700 ±7.5 A peak limit [HIOKI]. Channel `ai3` reads about 20 % lower than `ai0`/`ai2`.
- Vibration run names for loaded runs carry the suffix "_RPMFix" (meaning undocumented). The unbalance run name says "584mg" where the file name says 0583mg.

---

## 9. Implications for the planned KAIST replication

- **Teacher pairing (vibration + current).** On the varying-load set, pair windows only at the run level, or by relative time after a coarse offset correction. Do not assume sample synchrony. Exclude, or treat as unpaired, the three BPFO 0.3 mm conditions. Correct the 0 Nm BPFI 0.3/1.0 mm current labels first. Resample current from 25,608.2 Hz to 25,600 Hz (or both streams to a common rate).
- **Current-only student input.** Use one phase (`ai0`) for all classes, or drop BPFO. Otherwise the channel-availability pattern leaks the outer-race label.
- **Bearing-grouped cross-fitting.** KAIST has at most one specimen per (fault, severity) and apparently one healthy bearing. Report KAIST mainly as an **unseen operating condition** test (leave-one-load-out: 0/2/4 Nm). Any grouped cross-fitting there is **leave-one-severity-specimen-out** for the faulty classes and must be described as such. The healthy class cannot be grouped by bearing.
- **Varying-speed part.** One specimen per class; current at 100 kHz and vibration at 25.6 kHz from separate DAQs. Synchrony is documented only for the speed data, and the reference stream is unclear. File-level checks are pending (see open issues).
- **Classes for a bearing-fault replication.** Using unbalance and misalignment adds non-bearing classes recorded with the healthy bearing. Decide explicitly whether to include them.

---

## 10. Open issues (to check when the varying-speed zips arrive, or to ask the authors)

1. Contents of `part1.zip`, `part2.zip` and `part3.zip` (which states and files each holds). Not documented anywhere.
2. Varying-speed CSV layout: the actual columns and the "Time Stamp" units and epoch. Is current really 100 kHz? Is the rpm file sampled with vibration (SCADAS) or with current (NI)? Is rpm the motor speed or the shaft speed?
3. Are vibration and current in the varying-speed part concurrent or offset (as in the varying-load part)? Are the seven 300-s files contiguous?
4. Number of physical specimens per class and severity, and reuse across loads and between housings A and B. Inferred here from timestamps, not documented.
5. The 0 Nm BPFI 0.3/1.0 mm current label swap. Confirm with spectral evidence before relabelling.
6. Why the BPFO current has a single phase. Why BPFO 0.3 mm has no concurrent current recording.
7. Meaning of the load values (brake torque or torque-meter reading), the unbalance mounting radius, the defect manufacturing method for the varying-load part, and the defect sizes for the varying-speed part.
8. Supply frequency and drive (VFD) for both parts. About 48.5 Hz is observed in the varying-load part.
9. The accelerometer spec (PCB 352C34) could not be verified because the vendor page returned 403.
