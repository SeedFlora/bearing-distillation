# Paderborn University (KAt) Bearing DataCenter: verification of the dataset documentation

Project: "Transferability-Aware Cross-Modal Distillation for Current-Only Bearing Fault Diagnosis under Unseen Operating Conditions" (B. Juarto, BINUS University; target journal IJCDS). The method is a hypothesis under test, not an established contribution.

Report date and access date for every source below: **2026-11-07**. Scope: primary-source verification only. No bearing dataset was downloaded for this report. The `.rar` archives had already been downloaded by the separate data process (byte counts match the server, see `E:\bahrain\manifests\provenance\paderborn_downloads.tsv`). I read those local copies without changing them, as follows:
- I listed the contents of all 32 archives.
- I copied the two documentation PDFs out of each archive into `D:\bahrain-data\raw\literature\kat_bdc_archive_docs\<ID>\`.
- I streamed only the 116-byte MAT header of each of the 2,560 `.mat` files.
- I read the full `.mat` contents only for the six bearings that the data process had already extracted (K001, KA01, KA04, KB23, KI01, KI04).

Results from these local data files are marked **[local data]** and kept apart from statements taken from the documentation.

---

## 0. Verification summary

| # | Item | Expected | Verified value (source) | Status |
|---|---|---|---|---|
| 1 | Licence | CC BY-NC 4.0 | CC BY-NC 4.0; non-commercial academic use permitted; citation of the paper and the KAt-DataCenter required; commercial use requires contacting the author [S1], [S10 p.9] | Confirmed |
| 2a | Phase currents | 2 phases | Two motor phase currents, "Current u, v" [S10 Fig. 5, p.7]; file channels `phase_current_1`, `phase_current_2` [local data] | Confirmed. The 1→u, 2→v mapping is not documented |
| 2b | Current transducer | LEM | LEM CKSR 15-NP, accuracy 0.8 % of I_PN = 15 A, 25 kHz low-pass [S10 p.7]; 4th-order Bessel, 25 kHz [S5], [S13 logs] | Confirmed |
| 2c | Vibration sensor | PCB 336C04 | PCB Piezotronics 336C04 piezoelectric accelerometer, Kistler 5015(A) charge amplifier, 30 kHz low-pass (2nd order); mounted at the adapter at the top end of the bearing module [S10 p.7], [S5], [S13 logs] | Confirmed |
| 2d | Sampling rates | 64 kHz / 64 kHz / 4 kHz / 1 Hz | Current 64 kHz and vibration 64 kHz [S10 p.7; logs]. Mechanical channels (force, torque, speed) 4 kHz and temperature 1 Hz: **stated only in the measuring logs** [S13]; the paper says only "lower sampling rates" [S10 p.7] | Confirmed (4 kHz and 1 Hz from the logs) |
| 2e | Record duration | 4 s | "20 measurements of 4 seconds each" [S3], [S4], [S10 p.8] | Confirmed. Sample counts vary, see §2.4 [local data] |
| 2f | Recordings per bearing per condition | 20 | 20 [S3], [S4], [S10 p.8]; all 32 archives contain the 80 expected file names [local data] | Confirmed |
| 2g | Inverter switching frequency | – | 16 kHz, KEB Combivert 07F5E 1D-2B0A [S10 p.7] | Documented |
| 3 | Operating conditions | 4 codes | N15_M07_F10, N09_M07_F10, N15_M01_F10, N15_M07_F04; "All three parameters were kept constant for each measurement" [S4], [S10 Table 6 and §4.2, p.8] | Confirmed |
| 4 | Bearing table | 6 healthy / 12 artificial / 14 real | 6 / 12 / 14 [S3], [S10 p.8 and Tables 4, 5, 7] | Confirmed. See §4 for discrepancies |
| 4a | KA*/KI* with damage on both rings? | – | **Yes, for KI04 and KI14** according to their official fact sheets (secondary outer-ring particle-caused indentations, extent "n/a"). Paper Table 5 lists only "IR" for them (combination "M"). No KA* bearing documents inner-ring damage | Discrepancy between paper and fact sheets |
| 4b | KB23/KB24/KB27 | Combined, not ball faults | Combined inner and outer raceway damage. "Damage at the rolling elements was not observed" [S10 p.6]; "multiple damages at both raceways, at inner and outer ring (KB23, KB24 and KB27)" [S10 §7.4, p.13] | Confirmed |
| 5 | Independence | – | One physical bearing per code, measured under all 4 settings, almost always in one session of 0.7–2.6 h on one day, in a fixed order. Measurements span 2014-06-04 to 2015-10-16. 5 of the 6 healthy bearings were measured in Sep–Oct 2015 by one operator; most damaged bearings were measured in 2014 and early 2015 [S13 logs; local MAT headers] | Major confound, see §5 |
| 6 | readme_versions.txt | – | One line: KI03 fact-sheet correction on 2016-07-13 [S9]. Undocumented re-issues of KA01, KI01, KI07 and KI18 on 2016-06-15 [S8]. KA04 contains duplicated recordings [S13 log remark; local data] | See §6 |

---

## Sources (all accessed 2026-11-07)

| ID | Source | URL | Access level | Local copy |
|---|---|---|---|---|
| S1 | KAt Bearing DataCenter, overview page (EN) | https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter | full_text | `D:\bahrain-data\raw\literature\kat_bdc_overview\page.html` |
| S2 | Overview page, DE URL (body text in English) | https://mb.uni-paderborn.de/kat/forschung/bearing-datacenter | full_text | `...\kat_bdc_overview_de\page.html` |
| S3 | Data Sets and Download | https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter/data-sets-and-download | full_text | `...\kat_bdc_datasets\page.html` |
| S4 | Operating Conditions | https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter/operating-conditions | full_text | `...\kat_bdc_operating_conditions\page.html` |
| S5 | Test rig and measurement equipment | https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter/test-rig-and-measurement-equipment | full_text | `...\kat_bdc_test_rig\page.html` |
| S6 | Bearing Damage | https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter/bearing-damage | full_text | `...\kat_bdc_bearing_damage\page.html` |
| S7 | Publication and references | https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter/publication-and-references | full_text | `...\kat_bdc_publications\page.html` |
| S8 | Archive directory listing (Apache index; listing only) | https://groups.uni-paderborn.de/kat/BearingDataCenter/ | full_text | `...\kat_bdc_archive_listing\listing.html` |
| S9 | readme_versions.txt (112 bytes, Last-Modified Wed, 13 Jul 2016 08:08:49 GMT) | https://groups.uni-paderborn.de/kat/BearingDataCenter/readme_versions.txt | full_text | `...\kat_bdc_readme_versions\readme_versions.txt` (SHA-256 0458cfdc…0031be0, identical to the data process copy) |
| S10 | Lessmeier, Kimotho, Zimmer, Sextro (2016), PHM Society European Conference 3(1), DOI 10.36001/phme.2016.v3i1.1577, PDF (17 pp.) | https://papers.phmsociety.org/index.php/phme/article/download/1577/542 (byte-identical to https://mb.uni-paderborn.de/fileadmin-mb/kat/PDF/Veroeffentlichungen/20160703_PHME16_CM_bearing.pdf, SHA-256 c1f75c79…b0955f84) | full_text | `...\lessmeier2016condition_phms\paper.pdf`, `...\lessmeier2016condition_kat_pdf\paper.pdf` |
| S11 | PHM Society article landing page | https://papers.phmsociety.org/index.php/phme/article/view/1577 | full_text (landing page) | `...\lessmeier2016condition_landing\landing.html` |
| S12 | Crossref metadata and DOI BibTeX | https://api.crossref.org/works/10.36001/phme.2016.v3i1.1577 ; https://doi.org/10.36001/phme.2016.v3i1.1577 | metadata | `...\lessmeier2016condition_crossref\` |
| S13 | Official per-bearing fact sheets `<ID>/<ID>.pdf` ("Profile of rolling bearing damage") and measuring logs `<ID>/measuring_log_<ID>.pdf`, distributed inside each archive https://groups.uni-paderborn.de/kat/BearingDataCenter/<ID>.rar | (inside archives) | full_text (all 64 PDFs read) | `D:\bahrain-data\raw\literature\kat_bdc_archive_docs\<ID>\<ID>\` |
| S14 | Lessmeier, Enge-Rosenblatt, Bayer, Zimmer (2014), PHM Society European Conference 2(1), DOI 10.36001/phme.2014.v2i1.1488 (earlier rig paper cited by S10 for the bearing-module design) | https://papers.phmsociety.org/index.php/phme/article/download/1488/456 | full_text (§2.1 and the start of §4 read) | `...\lessmeier2014data\paper.pdf` |
| S15 | "Accelerated lifetime test rig" page linked from S5 | https://mb.uni-paderborn.de/en/kat/research/prueftechnik0/lp | **HTTP 404** (not accessible) | – |

The German URLs of the subpages (`/kat/forschung/bearing-datacenter/{test-rig-and-measurement-equipment, data-sets-and-download, operating-conditions, bearing-damage}`) were also fetched. They carry the same English body text as the EN pages and add no information. The only PDF linked from any KAt Bearing DataCenter page is the 2016 paper (S10). The KAt site has **no separate factsheet or documentation PDF**. The per-bearing fact sheets and measuring logs exist only inside the archives (S3: "systematic description of the bearing damage by uniform fact sheets and a measuring log, which can be downloaded with the data").

---

## 1. Licence and requested citation

**Dataset licence: CC BY-NC 4.0 (confirmed).**

- S1 (overview page, body text): "The data is licensed under the Creative Commons Attribution-NonCommercial 4.0 International Licence. To view a copy of this licence, visit http://creativecommons.org/licenses/by-nc/4.0/. Non-commercial academic use of the data is permitted, but a citation of the source is required. Please cite the following publication and include the author's name, institution and a link to the KAt-DataCenter: Christian Lessmeier et al., KAt-DataCenter: mb.uni-paderborn.de/en/kat/research/bearing-datacenter, Chair of Design and Drive Technology, Paderborn University. For commercial use, please contact the author."
- S2 (DE URL) has the same statement in US spelling ("License", "Noncommercial academic use of the data is allowed, but a citation of the origin is required"). Its link points to `mb.uni-paderborn.de/kat/forschung/bearing-datacenter`.
- S10, §5, p.9: "The data is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License.⁵ Noncommercial academic use of the data is explicitly allowed, but a citation of the origin is required and expected.⁶ For commercial use, please contact the author." Footnote 6: "Please cite this paper and give name of the author, institute and link to the Kat-DataCenter: Christian Lessmeier et al., KAt-DataCenter: http://mb.uni-paderborn.de/kat/datacenter, Chair of Design and Drive Technology, University Paderborn."
- **The legacy URL in the paper no longer works.** `http://mb.uni-paderborn.de/kat/datacenter` redirects to https and returns HTTP 404 (checked 2026-11-07). Use the URL given on S1.
- The paper's own licence is different from the dataset licence. The PDF footnote on p.1 says "Creative Commons Attribution 3.0 United States License", and Crossref says `http://creativecommons.org/licenses/by/3.0/us/` [S12]. The landing-page badge says "Creative Commons Attribution 3.0 Unported License" [S11]. This affects only the reuse of figures and text from the paper, not the data.

**Recommended citation pair for the IJCDS manuscript:**
1. Publication. Official title from the PDF title block [S10 p.1] and Crossref [S12]: C. Lessmeier, J. K. Kimotho, D. Zimmer, W. Sextro, "Condition Monitoring of Bearing Damage in Electromechanical Drive Systems by Using Motor Current Signals of Electric Motors: A Benchmark Data Set for Data-Driven Classification," *PHM Society European Conference*, vol. 3, no. 1, 2016 (published 5 Jul 2016), doi:10.36001/phme.2016.v3i1.1577. Crossref lists no page range; the PDF has pages 1–17.
2. Dataset: "Christian Lessmeier et al., KAt-DataCenter: https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter, Chair of Design and Drive Technology, Paderborn University" (wording from S1).

Title variants to avoid: the S1 EN page lists the paper as "...Drive Systems Using Motor Current Signals: A Benchmark Data Set..." and S7 lists "...Using Motor Current Signals from Electric Motors". S7 also misprints the second author as "Kimotho, J. Kimotho". Use the Crossref title. DOI BibTeX (doi.org, S12): `@article{Lessmeier_2016, title={Condition Monitoring of Bearing Damage in Electromechanical Drive Systems by Using Motor Current Signals of Electric Motors: A Benchmark Data Set for Data-Driven Classification}, volume={3}, ISSN={2325-016X}, DOI={10.36001/phme.2016.v3i1.1577}, number={1}, journal={PHM Society European Conference}, publisher={PHM Society}, author={Lessmeier, Christian and Kimotho, James Kuria and Zimmer, Detmar and Sextro, Walter}, year={2016}, month=July}`.

Practical implication: academic, non-commercial use in the IJCDS paper is allowed with both citations. Any redistributed derived data (for example preprocessed windows) must stay under NC terms with attribution.

---

## 2. Test rig, sensors and acquisition

### 2.1 Documented set-up

| Element | Documented value | Source and location |
|---|---|---|
| Rig layout | "electric motor (1), a torque-measurement shaft (2), a rolling bearing test module (3), a flywheel (4) and a load motor (5)" | S10 §4.1, p.7, Fig. 4 |
| Drive motor | "425 W Permanent Magnet Synchronous Motor (PMSM) with a nominal torque of T = 1.35 Nm, a nominal speed of n = 3,000 rpm, a nominal current of I = 2.3 A and a pole pair number p = 4 (Type SD4CDu8S-009, Hanning Elektro-Werke GmbH & Co. KG)" | S10 §4.1, p.7; S5 "Hanning synchronous motor: 425 W, 3,000 1/min, 1.35 Nm"; logs "Hanning-Motor SD4CDu8S-009/425W/Y230V" |
| Inverter | "frequency inverter (KEB Combivert 07F5E 1D-2B0A) with a switching frequency of 16 kHz" | S10 §4.1, p.7; same model in all 32 logs [S13] |
| Load motor | "PMSM with a nominal torque of 6 Nm (power of 1.7 kW)" | S10 p.7; S5 "Siemens synchronous servomotor: 1.7 kW, 3,000 1/min, 6 Nm"; logs "Siemens-Motor 1FT7062-1AF70-1DG1" |
| Phase currents measured | "The motor phase currents are measured by a current transducer of the type LEM CKSR 15-NP with an accuracy of 0.8 % of I_PN = 15 A. The MCS are then filtered by a 25 kHz low-pass filter and converted ... with a sampling rate of 64 kHz." Measured "externally between motor and inverter". The Figure 5 schema labels the current path **"Current u, v"** (two phases) | S10 §4.1, p.7, Fig. 5 (rendered and checked visually) |
| Current anti-aliasing | "Bessel-Filter 4th order with a filter frequency of 25 kHz" (S5); "current measurement box (self-construction): current transformer LEM Typ CKSR 15-NP, Bessel-Filter (4th order, cut-off frequency: 25 kHz)" (logs) | S5 Technical data; S13 all 32 logs |
| Vibration sensor and mounting | "The acceleration of the bearing housing is measured at the adapter at the top end of the rolling bearing module using a piezoelectric accelerometer (Model No. 336C04, PCB Piezotronics, Inc.) and a charge amplifier (Type 5015A, Kistler Group) with a low-pass filter at 30 kHz. The signal is digitalized and saved synchronously to the MCS with a sampling rate of 64 kHz." Also: "An adapter gives the possibility to measure the vibration of the inner housing, which holds the test bearing in the main direction of the load." | S10 §4.1, p.7 |
| Vibration filter | "charging amplifier type 5015, filter 30 kHz (2nd order)" (S5); "vibration transducer 336C04 (97/F/3, 100 mV/g, PCB Piezotronics Inc.), charge amplifier type 5015 (filter 30 kHz , 2. Order, Kistler)" (logs) | S5; S13 |
| Additional channels | "measured synchronously to the motor currents and vibration signal but with lower sampling rates: the radial force on the bearings (Compression and Tension Force Sensor Type K11, Lorenz, 10 kN), the load torque at the torque-measuring shaft, the rotational speed (Torque Transducer Model 305, Magtrol, 2 Nm) and the oil temperature in the bearing module" | S10 p.7 |
| Sampling rates (all groups) | "motor current sampling frequency: 64 kHz", "vibration sampling frequency: 64 kHz", "sampling frequency of mechanic parameters (load force, load torque, speed): 4 kHz", "temperature sampling frequency: 1 Hz"; "Simulink-model: Messung_Strom64kHz_Mech4kHz_Temp1Hz_05_14" | S13, identical in all 32 measuring logs |
| Acquisition hardware | "Processor-Board DS 1006 Single Core (with DS2004) (dSpace GmbH)" | S5; S13 |
| Temperature sensor | "MINI MCR-SL-TC_UI-NC (Phoenix Contact)" | S5; S13 |
| Radial load | "constant radial load, which can be continuously adjusted up to 10 kN before each experiment" | S10 p.7 |
| Record duration and count | "For each of the settings, 20 measurements of 4 seconds each were recorded." | S4; S10 §4.2, p.8; S3 |
| Bearing type | "ball bearings of type 6203"; manufacturers FAG, MTK and IBU/IBB; "eight rolling elements ... characteristic kinematic frequencies do not vary more than 1-2%" | S10 §3, p.5; S3 |

Not documented anywhere I read:
- the cutoff of any anti-aliasing filter on the 4 kHz mechanical channels or on the 1 Hz temperature channel;
- physical units or scaling of the stored channels (the `Unit` fields in the files are empty, see §2.3);
- which inverter phase is u and which is v, and the mapping to `phase_current_1` and `phase_current_2`.

Derived only, not a documented value: with p = 4 the electrical supply frequency would be 100 Hz at 1500 rpm and 60 Hz at 900 rpm. S10 Fig. 6 and 7 give a shaft frequency of f_n = 25 Hz at 1500 rpm.

Context [S14, §2.1, p.2]: the earlier proof-of-concept configuration of the same rig used "a current transducer of the type MCTS 60/ IT60-S", a "12.5 kHz low-pass filter" and "a sampling rate of 100 kHz". That configuration is **not** the one in the benchmark data. All 32 benchmark logs list the LEM CKSR 15-NP / 25 kHz / 64 kHz chain. Values from S14 must not be reused when describing this dataset.

### 2.2 Inconsistencies in the sensor documentation

- S5 writes "vibration sensor: Model No. 336C04 (PCB Piezotronics Inc.), Kistler". Read with S10 and the logs, "Kistler" refers to the charge amplifier, not to the sensor.
- S5 names the force-box manufacturer as "Lorents-Messtechnik". The logs write "Lorenz Messtechnik GmbH" and the paper writes "Lorenz".
- The charge amplifier is "Type 5015A" in S10 and "type 5015" in S5 and the logs.

### 2.3 Channel names inside the files [local data]

I inspected 480 files from the six bearings already extracted by the data process. Every file holds one MATLAB 5.0 struct named after the file (for example `N15_M07_F10_K001_1`) with fields `Info, X, Y, Description`. `Y` always contains seven channels in this order:

| Y.Name | Y.Raster | Samples per 4-s file (typical) |
|---|---|---|
| `force` | `Mech_4kHz` | 16,001 |
| `phase_current_1` | `HostService` | ~256,001 |
| `phase_current_2` | `HostService` | ~256,001 |
| `speed` | `Mech_4kHz` | 16,001 |
| `temp_2_bearing_module` | `Temp_1Hz` | 4–5 |
| `torque` | `Mech_4kHz` | 16,001 |
| `vibration_1` | `HostService` | ~256,001 |

Other observations from the same files:
- All `Unit` fields are empty.
- `Description.Recording.StopCondition` = "Time limit: 4.000000".
- `Description.General.Origin` = "Software revision: modell_autass_05_14.sdf ... Platform [DS1006 Processor Board, ...]" in all 480 files.

Only these six bearings were opened. The remaining 26 archives were not extracted, so the channel names there are unverified, though the identical logs make the same layout likely.

### 2.4 Time base and sample counts [local data, not documented]

The 64 kHz group (`HostService` raster) does not always hold 256,001 samples per 4-s file. In the six bearings checked:
- counts range from 255,997 to 282,475;
- only 21–44 of 80 files per bearing hold exactly 256,001 samples;
- 35–50 of 80 files per bearing contain at least one time step deviating by more than 20 % from 1/64,000 s;
- example: `N15_M01_F10_KB23_19` has 282,475 samples in 3.999999 s, including one gap of 21.8 ms.

In a regular file (`N15_M07_F10_K001_1`), the steps alternate between 15.398 µs and 15.826 µs and average exactly 1/64,000 s. Files with extra samples have shorter steps on average. The 4 kHz group has 16,001–16,008 samples. Every file spans 3.99998–4.00001 s.

Consequence for preprocessing (our recommendation): do not assume 256,000 equally spaced samples. Either resample onto a uniform 64 kHz grid using the stored `X` time vector, or crop and flag files whose time base is irregular.

---

## 3. Operating conditions

S4 (table and text) and S10 (§4.2 and Table 6, p.8; positions of table words checked):

| No. | Speed [rpm] | Load torque [Nm] | Radial force [N] | Code |
|---|---|---|---|---|
| 0 | 1500 | 0.7 | 1000 | N15_M07_F10 |
| 1 | 900 | 0.7 | 1000 | N09_M07_F10 |
| 2 | 1500 | 0.1 | 1000 | N15_M01_F10 |
| 3 | 1500 | 0.7 | 400 | N15_M07_F04 |

- Constancy within a recording: "To ensure comparability of the experiments, fixed levels were defined for each parameter ... All three parameters were kept constant for each measurement" (S4). S10 p.8 says: "All three parameters were kept constant for the time of each measurement."
- Temperature: "Another parameter is the temperature, which was kept roughly at 45-50 °C during all experiments" (S4; S10 p.8). The logs record a "temperature reached" after preheating of 45–56.2 °C, so several bearings exceed 50 °C: KA04 56 °C, KB23 56.2 °C, K004 and K005 54 °C, KI14 52.1 °C. KI18 is "-" (not recorded) [S13].
- The S4 table header reads "Load Torque3 [Nm]". The stray "3" is in the HTML.
- The logs call the settings K0–K3: "K0: N15_M07_F10_... K1: N09_M07_F10_... K2: N15_M01_F10_... K3: N15_M07_F04_..." [S13].
- S10 §8 (p.15) states that variable operating conditions remain an open question: "Industrial application requires the detection of damages under variable operating conditions."

---

## 4. Complete bearing table

Sources:
- Healthy bearings: S10 Table 7 (p.8).
- Artificial damage: S10 Table 4 (p.5) and §3.1 (p.5: "all the artificial damages are single point damages without a repetition or combination with other damages").
- Real damage: S10 Table 5 (p.6).
- All bearings: official fact sheets [S13].

All four tables were re-extracted with word coordinates to rule out column mixing.

Definitions:
- S, R and M mean single, repetitive and multiple damage. "Multiple damage: Different damage symptoms occur in the bearing or identical damage symptoms occur on different bearing components. This option can include repetitive damages" [S10 §2, p.4].
- Extent levels follow Table 2 (p.4), with limits for the 6203: level 1 ≤ 2 mm, level 2 > 2 mm, level 3 > 4.5 mm, level 4 > 13.5 mm, level 5 > 31.5 mm. For multiple damages the paper notes that they "were characterized according to the damage with the highest extent" [S10 p.6].
- "Single point" versus "distributed" uses "the diameter of the rolling elements" as the dividing length [S10 p.4].

| ID | Class | Origin | Method (paper) | Location | Extent | Combination / arrangement / characteristic | Run-in [h] | Manufacturer (fact sheet) | Notes from fact sheet |
|---|---|---|---|---|---|---|---|---|---|
| K001 | healthy | none | – | – | – | – | >50 (1000–3000 N, 1500–2000 min⁻¹) | IBU | |
| K002 | healthy | none | – | – | – | – | 19 (3000 N, 2900 min⁻¹) | IBU | log designation "10-03" |
| K003 | healthy | none | – | – | – | – | 1 (3000 N, 3000 min⁻¹) | IBU | |
| K004 | healthy | none | – | – | – | – | 5 (3000 N, 3000 min⁻¹) | IBU | log: measured right after the 5 h run-in |
| K005 | healthy | none | – | – | – | – | 10 (3000 N, 3000 min⁻¹) | IBU | log: measured right after the 10 h run-in |
| K006 | healthy | none | – | – | – | – | 16 (3000 N, 2900 min⁻¹) | IBU | log designation "18-03" |
| KA01 | outer | artificial | EDM | OR raceway | 1 | S, no repetition, single point | – | MTK | 0.25 mm long, 1 mm deep, width total; "EDM machining" |
| KA03 | outer | artificial | electric engraver | OR | 2 | S, single point | – | MTK | 3 mm × 2 mm |
| KA05 | outer | artificial | electric engraver | OR | 1 | S, single point | – | IBU | 1 mm × 1 mm |
| KA06 | outer | artificial | electric engraver | OR | 2 | S, single point | – | IBU | 3 mm × 3 mm |
| KA07 | outer | artificial | drilling | OR | 1 | S, single point | – | IBU | 0.9 mm, "drilled" |
| KA08 | outer | artificial | drilling | OR | 2 | S, single point | – | IBU | 2 mm, "drilled"; fact sheet component printed **"AR"** |
| KA09 | outer | artificial | drilling | OR | 2 | S, single point | – | IBU | 3 mm, "drilled" |
| KI01 | inner | artificial | EDM | IR raceway | 1 | S, single point | – | MTK | 0.25 mm, depth 1 mm; fact sheet method **"n/a"** |
| KI03 | inner | artificial | electric engraver | IR | 1 | S, single point | – | MTK | < 2 mm × < 1 mm (corrected sheet of 2016-07-13) |
| KI05 | inner | artificial | electric engraver | IR | 1 | S, single point | – | IBU | 1 mm × 1 mm |
| KI07 | inner | artificial | electric engraver | IR | 2 | S, single point | – | IBU | 2.2 mm × 1 mm |
| KI08 | inner | artificial | electric engraver | IR | 2 | S, single point | – | IBU | 3 mm × 1 mm |
| KA04 | outer | real (acc. lifetime) | fatigue: pitting | OR | 1 | S, no repetition, single point | – | FAG | 2 mm × 3 mm; sample 15-03; 12:01 h, 2,166,300 cycles |
| KA15 | outer | real | plastic deform.: indentations | OR | 1 | S, no repetition, single point | – | FAG | < 1 mm; sample 13-04; 6:01 h |
| KA16 | outer | real | fatigue: pitting | OR | 2 | R, random, single point | – | MTK | two OR pittings, 2 mm and 3 mm, both level 2; sample 15-04; 9:01 h |
| KA22 | outer | real | fatigue: pitting | OR | 1 | S, no repetition, single point | – | IBU / IBB | < 2 mm × 1 mm; sample 19-01; 14:01 h; load 3000 N |
| KA30 | outer | real | plastic deform.: indentations | OR | 1 | R, random, distributed | – | MTK | < 1 mm; sample 15-01; 21:01 h |
| KI04 | inner | real | fatigue: pitting | IR (Table 5) | 1 | M, no repetition, single point | – | MTK | **damage 2: OR particle-caused indentations, random, extent n/a**; sample 15-02; 12:01 h |
| KI14 | inner | real | fatigue: pitting | IR (Table 5) | 1 | M, no repetition, single point | – | MTK | **damage 2: OR particle-caused indentations 1 mm, random, extent n/a**; sample 11-02; 21:01 h |
| KI16 | inner | real | fatigue: pitting | IR | 3 | S, no repetition, single point | – | FAG | 6 mm, width total; sample 14-04; 3:01 h |
| KI17 | inner | real | fatigue: pitting | IR | 1 | R, random, single point | – | MTK | two IR pittings of 1 mm; sample 16-02; 19:01 h |
| KI18 | inner | real | fatigue: pitting | IR | 2 | S, no repetition, single point | – | MTK | 2.5 mm, width total; sample 16-04; 7:01 h |
| KI21 | inner | real | fatigue: pitting | IR | 1 | S, no repetition, single point | – | FAG | 1 mm × 2 mm; sample 18-01; 20:01 h |
| KB23 | combined | real | fatigue: pitting | IR (+OR) | 2 | M, random, single point | – | MTK | 3 damages: IR 1.5 mm (L1), IR 3 mm (L2), OR 3 mm (L2); fact sheet codes "R" for each; sample 11-04; 21:01 h |
| KB24 | combined | real | fatigue: pitting | IR (+OR) | 3 | M, no repetition, distributed | – | FAG | IR pitting 9.4 mm, width total (L3, distributed) + OR indentations < 1 mm (extent n/a); sample 12-01; 15:01 h |
| KB27 | combined | real | plastic deform.: indentations | OR + IR | 1 | M, random, distributed | – | FAG | OR and IR indentations < 1 mm (L1, distributed); sample 11-01; 21:01 h |

Lifetime-test fields (sample number, installation site, cycles, h:min, load, speed 2900 min⁻¹) come from fact sheet p.1 [S13]. Geometry from the fact sheets: pitch circle diameter 28.55 mm for FAG and 29.05 mm for IBU, MTK and IBU/IBB; 8 balls of 6.75 mm [S13 p.1]. A machine-readable version with per-bearing source locations is at `E:\bahrain\manifests\paderborn_bearing_factsheet.json`.

### 4.1 Explicit answers

- **Does any KA*/KI* bearing have damage on both rings?** Yes, two do according to their official fact sheets.
  - **KI04**: damage 1 is IR fatigue pitting ("fatigue below the surface", 2 mm, level 1). Damage 2 is OR "plastic deformation / deformation by foreign objects / particle-caused indentations", arrangement "random", extent "n/a", with length, width and depth left blank.
  - **KI14**: damage 1 is IR pitting (1 mm, level 1). Damage 2 is OR particle-caused indentations (1 mm × 1 mm, random, extent n/a).
  - Both have combination "M" in the fact sheets and in S10 Table 5. Table 5 nonetheless lists their bearing element as "IR" only, and S10 Table 10 (p.12) uses both as "Inner ring damage (Class 3)".
  - All other KI* and all KA* fact sheets list damage on one ring only. KA08's component is printed "AR" (the legend defines only OR and IR); S10 Table 4 says OR.
  - Conclusion: KI04 and KI14 should be treated as IR-dominant with a minor secondary OR damage. Our suggestion is to flag them in a label-noise sensitivity analysis.
- **Are KB23, KB24 and KB27 combined inner plus outer damage rather than ball faults?** Yes.
  - Table 5 elements: KB23 "IR (+OR)", KB24 "IR (+OR)", KB27 "OR + IR" [S10 p.6].
  - S10 §7.4 (p.13): "bearings with multiple damages at both raceways, at inner and outer ring (KB23, KB24 and KB27). According to the dominant damage type KB23 and KB24 were assigned to the inner ring damage (class 3), while KB27 was assigned to the outer ring damage (class 2)."
  - S10 §3.2 (p.6): "Damage at the rolling elements was not observed."
  - All fact-sheet damages are on the raceways (the "Position of damage" field reads "raceway").
  - The dataset contains **no rolling-element (ball) faults**.

### 4.2 Discrepancies between documentation sources (verified, with locations)

1. S10 §6 (p.9) text: "Two single point damages, one at the inner ring (KA04) and one at the outer ring (KI18)". The rings are swapped relative to Tables 4 and 5, the fact sheets, and the figures: Fig. 6 shows "N15_M07_F10_KA04_1" with the outer-race frequency f_o = 76.25 Hz, and Fig. 7 shows "N15_M07_F10_KI18_1" with f_i = 123.3 Hz.
2. S10 Table 1 (p.3) worked example for KB24 lists "Component: outer ring" for the 9.4 mm, level-3, distributed damage. Table 5 says "IR (+OR)", and the KB24 fact sheet puts the 9.4 mm damage on the IR and the < 1 mm indentations on the OR.
3. S10 §3.2 (p.6) says "Indentations were found at the outer ring only". Table 5 and the KB27 fact sheet list IR indentations for KB27.
4. S3 and S10 §5 (p.9) refer to the healthy bearings as "see Table 6". The healthy-bearing table is Table 7; Table 6 lists the operating parameters.
5. The KI04 and KI14 fact sheets list an OR damage that Table 5's element column omits (see §4.1).
6. The KB23 fact sheet gives combination "R" for each of its three damages; Table 5 gives "M".
7. The KI01 fact sheet gives damage method "n/a"; Table 4 gives EDM. The KA01 sheet, for the same EDM geometry, says "EDM machining".
8. The KA08 fact sheet gives component "AR"; Table 4 gives OR.
9. The KI16 measuring log gives designation "6203-I16", an artificial-style code. The fact sheet gives sample number "14-04".
10. S5 links the accelerated-lifetime rig page, which returns HTTP 404 [S15].
11. No formal erratum exists for the paper. Crossref lists no correction or update notice for DOI 10.36001/phme.2016.v3i1.1577: the record has no `update-to` field, and the query `https://api.crossref.org/works?filter=updates:10.36001/phme.2016.v3i1.1577` returned 0 results [S12]. Items 1–4 above are therefore unpublished inconsistencies.

---

## 5. Independence of experimental units

Documented facts:
- **One physical bearing per code, measured under all four settings.** "For each of the settings, 20 measurements of 4 seconds each were recorded" [S4; S10 p.8]. Each archive holds exactly 4 × 20 files named `<setting>_<ID>_<1..20>.mat` (all 32 archives listed, no missing or extra names) [S8 archives, local listing]. Recordings of the same bearing under different settings are therefore **not** independent units. The bearing is the experimental unit.
- **Mounting.** "The ball bearings with different types of damage are mounted in the bearing test module to generate the experimental data"; the radial load "can be continuously adjusted up to 10 kN before each experiment" [S10 §4.1, p.7]. S14 (§2.1, p.3) describes the radial force as "generated by tightening a screw between the outer housing and the thread". No source says whether a bearing was re-mounted between settings or between sessions.
- **Preheating.** Every log records a preheating step. 30 bearings used "(F=2000 N; n=2000 1/min)", with durations of 25–135 min (KI03 and KI14 unrecorded). K004 and K005 used "(F=3000 N; n=3000 1/min)" with 0 min, and their remarks read (German, translated): "after the run-in period (5 h / 10 h at 3000 N and 3000 1/min) the measurement was carried out" [S13].
- **Measurement dates.** The logs date the measurements from 04.06.2014 (KI03) to 16.10.2015 (K004) [S13]. Three different operator names appear in the logs (anonymised here as A, B and C); KI03 and KI14 have none.
- **No documented rig changes during the campaign.** All 32 logs list the same motor, inverter, load motor, current box, accelerometer, charge amplifier, dSPACE board and Simulink model `Messung_Strom64kHz_Mech4kHz_Temp1Hz_05_14` [S13]. In the 480 files inspected, `Description.General.Origin` gives the same software revision `modell_autass_05_14` [local data].
- **Real damages come from shared lifetime-test runs.** The accelerated lifetime rig "powers a shaft with four test bearings of type 6203" [S10 §3.2, p.6]. The fact-sheet sample numbers and installation sites suggest groups of bearings that ran together. This grouping is our interpretation of the numbering scheme, which is not explained anywhere:
  - "11-xx": KB27 (11-01), KI14 (11-02), KB23 (11-04). All three show 21:01 h and 3,683,000 cycles.
  - "15-xx": KA30 (15-01), KI04 (15-02), KA04 (15-03), KA16 (15-04).
  - "16-xx": KI17 (16-02), KI18 (16-04).
  - "18-01" is KI21. The measuring log of healthy K006 carries the designation "18-03", and K002 carries "10-03".
  - In addition: "33 damages were recognized in 18 bearings out of a test amount of 108 bearings used in the lifetime test" [S10 p.6].

Session structure from the MAT-file header save times [local data; header text "Created on: ..." in rig-PC local time, no time zone stated]:
- 30 of 32 bearings were recorded in **one session on one day**, lasting 0.7–2.6 h, in the fixed order N15_M07_F10 → N09_M07_F10 → N15_M01_F10 → N15_M07_F04. KA04 is counted here: its original session on 2014-06-10 fits the pattern, apart from four files re-saved later (see below).
- **K004** started with N15_M01_F10, followed by N15_M07_F10, N09_M07_F10 and N15_M07_F04, all on 2015-10-16.
- **KI04** recorded N15_M01_F10 on 2015-07-09 (16:21–16:54) and the other three settings on 2015-07-10 (13:36–14:25). Its log is dated 13.07.2015.
- **KA04**: four files carry a 2015-03-02 save time (see §6).
- **K003**: the log is dated 17.09.2015, but all files were saved on 2015-09-22. The K003 log repeats K001's preheat values (37 min, 45 °C).
- Within a setting, the file index is not always in temporal order (for example `N15_M07_F10_KA09_1` was saved after `_5`).
- In the files I opened, the internal `Description.General.DateTime` precedes the header time by about 15–22 s (for example K001_1: 19:34:44 internal vs 19:35:06 header).

Date clusters (our grouping) and the class/operator confound:

| Period | Bearings (healthy in bold) | Operator |
|---|---|---|
| 2014-06-04 to 2014-08-07 | KI03, KA03, KA04, KI14, KI16, KI18, KI17, KI21, KA15, KA16, KA22, KB27 | A / B / none |
| 2014-11-10 to 2014-12-29 | KA01, KA05, KA06, KA07, KA08, KA09 | B |
| 2015-03-25 to 2015-03-27 | KB23, **K002**, KI05, KI07, KA30, KI08 | B |
| 2015-07-09/10 | KI04 | C |
| 2015-09-17 to 2015-10-16 | **K001**, KI01, KB24, **K003**, **K006**, **K005**, **K004** | C |

Five of the six healthy bearings were measured in the last cluster by operator C. Two of those (K004, K005) used a different warm-up protocol. Nearly all damaged bearings were measured 5–16 months earlier.

Class and manufacturer are also partly aliased (fact sheets, S13):
- healthy: IBU ×6;
- artificial: MTK (KA01, KA03, KI01, KI03) and IBU (others);
- real OR: FAG (KA04, KA15), MTK (KA16, KA30), IBU/IBB (KA22);
- real IR: MTK (KI04, KI14, KI17, KI18), FAG (KI16, KI21);
- combined: MTK (KB23), FAG (KB24, KB27).

Implications for the project (our assessment, not taken from the sources):
1. Grouping by bearing ID is necessary for cross-fitting the bridge regressors and for "unseen bearing" tests. It is not sufficient: a healthy-versus-damaged decision may be partly predictable from campaign, operator, warm-up or manufacturer. Report this as a limitation. Where feasible, add a sensitivity split restricted to bearings measured in a common period, for example the Sep–Oct 2015 cluster or the March 2015 cluster.
2. "Unseen operating condition" splits test generalisation within the same mounted bearing. Each bearing's held-out setting was recorded minutes after the training settings, with N15_M07_F04 almost always last and preceded by a manual change of the radial load. Combine condition hold-out with bearing hold-out when claiming generalisation to new bearings and new conditions.
3. Bearings that co-ran in one lifetime test (series 11, 15 and 16) are not independent damage-generation events. They mostly belong to different classes, so this is secondary, but it should be stated.

The per-bearing session table is in Appendix A.

---

## 6. readme_versions.txt and known file-version issues

**readme_versions.txt** [S9]: 112 bytes, Last-Modified "Wed, 13 Jul 2016 08:08:49 GMT", SHA-256 `0458cfdc33a09702e88a878b359c8c4f7606cf1d78ab4acab685a7a0b0031be0`. Full content (a single line):

> `2016-07-13:  update of profile of bearing damage KI03 (correction of mistakes in description of damage geometry)`

**Archive listing** [S8] has 32 `.rar` files and readme_versions.txt. The listing shows last-modified dates in server local time and sizes rounded to MB, for example K001.rar "2016-05-24 14:50 166M".
- 27 archives are dated 2016-05-24.
- **KA01 (2016-06-15 10:16), KI01 (10:17), KI07 (09:41) and KI18 (09:42)** were re-issued on 2016-06-15. Their fact-sheet PDFs carry creation dates of 2016-06-15. **This update is not mentioned in readme_versions.txt.** What changed is undocumented.
- **KI03** is dated 2016-07-13 10:04. Its fact sheet was created 2016-07-13, matching readme_versions.txt.
- The measuring-log PDFs of all bearings carry a creation date of 2016-04-18 [S13 PDF metadata].
- There is no checksum file on the server. Byte counts of the local copies match the HTTP Content-Length (provenance TSV).

**File issues documented in the measuring logs** [S13]:
- **KA04** (log remark, German; translated): "Data set N09_M07_F10_KA04_17.mat contained faulty data (the time series were in 2 vectors). Remedy: it was replaced by a copy of N09_M07_F10_KA04_18.mat with number 17, which now... The following data sets contained too few measuring points". The sentence and the list are truncated in the PDF.
  - [local data] `N09_M07_F10_KA04_17` is **identical** to `_18` in all seven channels and has the same internal DateTime.
  - In addition, `N15_M07_F04_KA04_5` is identical to `_19`, and `N15_M07_F04_KA04_6` and `_15` are identical to `_20`.
  - The four duplicating files are the documented replacement `_17` and `_5`, `_6`, `_15`. That the last three were also overwritten with copies is our inference from the truncated remark. All four carry the MAT save time 2015-03-02 and are the four smallest members in the archive (5.86–5.98 MB versus about 8.7 MB).
  - Result: **KA04 has 76 unique recordings, and only 17 unique ones for N15_M07_F04.** Deduplicate before computing any per-recording statistic or residual.
- **KI04** (log remark, German; translated): "Faulty files in the folder 'Fehlerhaft': without the 'Kistler' vibration sensor switched on". The distributed KI04 archive contains no such folder, only the 80 standard files and two PDFs [local listing].

**Duplicate check coverage** [local data]: K001, KA01, KB23, KI01 and KI04 showed no duplicated recordings (hash of `phase_current_1`, `phase_current_2` and `vibration_1`). The other 26 bearings were not checked. A duplicate-hash pass over all 2,560 files is recommended once they are extracted.

---

## 7. What remains unverified or undocumented

- The current-phase mapping (`phase_current_1` = u?).
- Physical units and scaling of all channels.
- Filters on the 4 kHz and 1 Hz channels.
- Whether bearings were re-mounted between settings or between KI04's two sessions.
- What changed in the 2016-06-15 re-issues (KA01, KI01, KI07, KI18).
- The truncated KA04 list of short files.
- The meaning of the lifetime-test sample numbers.
- The accelerated-lifetime rig page (HTTP 404).
- Channel layout and duplicates in the 26 archives not yet extracted.

---

## Appendix A. Per-bearing measurement sessions

Data: measuring-log date, preheat condition and duration, and "temperature reached" from [S13]. The save window and condition order come from the MAT headers [local data]. Operators are anonymised (A, B, C), and the names are left out on purpose.

| Bearing | Log date | MAT save window (local) | Span h | Condition order | Operator | Preheat | T reached | Max gap (min) |
|---|---|---|---|---|---|---|---|---|
| KI03 | 2014-06-04 | 2014-06-04 10:50 to 12:37 | 1.79 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | none recorded | F=2000 N; n=2000 1/min - | 50.6°C | 5.7 |
| KA03 | 2014-06-05 | 2014-06-05 15:40 to 16:52 | 1.19 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | A | F=2000 N; n=2000 1/min 38 min | 51°C | 4.6 |
| KA04 | 2014-06-10 | 2014-06-10 17:44 to 2015-03-02 10:52 | 6353.14 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | B | F=2000 N; n=2000 1/min 80 min | 56°C | 381047.2 (re-saved files) |
| KI14 | 2014-06-12 | 2014-06-12 14:36 to 16:21 | 1.74 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | none recorded | F=2000 N; n=2000 1/min - | 52.1°C | 15.4 |
| KI16 | 2014-06-16 | 2014-06-16 13:09 to 14:27 | 1.29 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | B | F=2000 N; n=2000 1/min 50 min | 48°C | 5.7 |
| KI18 | 2014-06-17 | 2014-06-17 12:37 to 13:53 | 1.26 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | A | F=2000 N; n=2000 1/min 135 min | -°C | 21.9 |
| KI17 | 2014-06-17 | 2014-06-17 15:59 to 16:53 | 0.9 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | A | F=2000 N; n=2000 1/min 25 min | 49.8°C | 3.5 |
| KI21 | 2014-07-29 | 2014-07-29 11:37 to 12:56 | 1.32 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | A | F=2000 N; n=2000 1/min 38 min | 50.6°C | 3.6 |
| KA15 | 2014-07-29 | 2014-07-29 15:09 to 15:55 | 0.77 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | A | F=2000 N; n=2000 1/min 28 min | 48,8°C | 3.1 |
| KA16 | 2014-08-01 | 2014-08-01 09:51 to 12:27 | 2.6 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | A | F=2000 N; n=2000 1/min 34 min | 49,6°C | 78.9 |
| KA22 | 2014-08-01 | 2014-08-01 14:44 to 15:39 | 0.91 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | A | F=2000 N; n=2000 1/min 34 min | 48.4°C | 2.9 |
| KB27 | 2014-08-07 | 2014-08-07 10:00 to 11:08 | 1.13 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | A | F=2000 N; n=2000 1/min 38 min | 49.4°C | 3.9 |
| KA01 | 2014-11-10 | 2014-11-10 10:20 to 11:50 | 1.5 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | B | F=2000 N; n=2000 1/min 50 min | 49°C | 11.7 |
| KA05 | 2014-11-14 | 2014-11-14 15:52 to 17:29 | 1.61 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | B | F=2000 N; n=2000 1/min 70 min | 46°C | 4.8 |
| KA06 | 2014-11-15 | 2014-11-15 09:59 to 11:18 | 1.32 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | B | F=2000 N; n=2000 1/min 70 min | 46°C | 3.2 |
| KA07 | 2014-12-23 | 2014-12-23 15:45 to 17:02 | 1.29 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | B | F=2000 N; n=2000 1/min 70 min | 48°C | 3.3 |
| KA08 | 2014-12-29 | 2014-12-29 11:00 to 12:17 | 1.3 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | B | F=2000 N; n=2000 1/min 70 min | 49°C | 8.0 |
| KA09 | 2014-12-29 | 2014-12-29 15:03 to 16:34 | 1.52 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | B | F=2000 N; n=2000 1/min 75 min | 51°C | 6.5 |
| KB23 | 2015-03-25 | 2015-03-25 12:21 to 13:48 | 1.45 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | B | F=2000 N; n=2000 1/min 70 min | 56.2°C | 5.0 |
| K002 | 2015-03-25 | 2015-03-25 15:45 to 17:01 | 1.26 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | B | F=2000 N; n=2000 1/min 65 min | 50.5°C | 5.1 |
| KI05 | 2015-03-26 | 2015-03-26 11:37 to 12:55 | 1.29 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | B | F=2000 N; n=2000 1/min 65 min | 48°C | 7.5 |
| KI07 | 2015-03-26 | 2015-03-26 14:57 to 17:25 | 2.48 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | B | F=2000 N; n=2000 1/min 65 min | 46°C | 24.9 |
| KA30 | 2015-03-27 | 2015-03-27 09:17 to 10:59 | 1.7 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | B | F=2000 N; n=2000 1/min 65 min | 46°C | 11.5 |
| KI08 | 2015-03-27 | 2015-03-27 12:03 to 13:14 | 1.19 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | B | F=2000 N; n=2000 1/min 65 min | 46°C | 3.5 |
| KI04 | 2015-07-13 | 2015-07-09 16:21 to 2015-07-10 14:25 | 22.07 | N15M01F10 > N15M07F10 > N09M07F10 > N15M07F04 | C | F=2000 N; n=2000 1/min 40 min | 47.2°C | 1242.0 (overnight) |
| K001 | 2015-09-17 | 2015-09-17 19:35 to 20:32 | 0.96 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | C | F=2000 N; n=2000 1/min 37 min | 45°C | 4.0 |
| KI01 | 2015-09-18 | 2015-09-18 10:41 to 11:32 | 0.84 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | C | F=2000 N; n=2000 1/min 36 min | 45°C | 4.4 |
| KB24 | 2015-09-21 | 2015-09-21 11:19 to 12:13 | 0.9 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | C | F=2000 N; n=2000 1/min 48 min | 45°C | 7.0 |
| K003 | 2015-09-17 | 2015-09-22 11:41 to 12:27 | 0.77 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | C | F=2000 N; n=2000 1/min 37 min | 45°C | 3.0 |
| K006 | 2015-10-07 | 2015-10-07 14:05 to 14:53 | 0.79 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | C | F=2000 N; n=2000 1/min 120 min | 46°C | 3.2 |
| K005 | 2015-10-14 | 2015-10-14 12:38 to 13:25 | 0.79 | N15M07F10 > N09M07F10 > N15M01F10 > N15M07F04 | C | F=3000 N; n=3000 1/min 0 min | 54°C | 3.7 |
| K004 | 2015-10-16 | 2015-10-16 17:11 to 17:53 | 0.7 | N15M01F10 > N15M07F10 > N09M07F10 > N15M07F04 | C | F=3000 N; n=3000 1/min 0 min | 54°C | 4.0 |

## Appendix B. Method notes and integrity

- **Web pages:** fetched with `curl` using a generic user agent into new, empty directories under `D:\bahrain-data\raw\literature\` and converted to text with a stdlib HTML parser. PDFs were read with PyMuPDF (`py -3.13 -I`). The tables in S10 were re-extracted with word coordinates, and Figure 5 was rendered to an image and checked visually.
- **Archive contents** were listed with Windows `tar.exe` (libarchive 3.8.9) without extraction. The two PDFs per archive were extracted into `D:\bahrain-data\raw\literature\kat_bdc_archive_docs\<ID>\`. The copies of the six already-extracted bearings are byte-identical to the data process extraction.
- **MAT headers:** the first 116 bytes of each of the 2,560 `.mat` members were streamed to stdout. Full `.mat` reads used `scipy.io.loadmat` and were limited to the six already-extracted bearings.
- **Nothing was executed** from the downloaded material.
- **SHA-256 (full) of the key sources:**
  - S10 PDF: `c1f75c79cfbcbcbfd24b32bf034cebb76d1c3ff7864827575d37387bb0955f84`
  - S14 PDF: `19e16853bcbd62328f095818e3abf36fbed4f9e53725d39a0751e66624e5ff6e`
  - S8 listing.html: `1ea8ad472791c44e0b196b0d85d4d356b37e2888010ba0168bb90d9cbcfb209c`
  - S9: `0458cfdc33a09702e88a878b359c8c4f7606cf1d78ab4acab685a7a0b0031be0`
  - S1: `305b24e91d1d82876d4fb4c64478189016a376beb8578ecdbd4b5415ab4facae`
  - S3: `1304076e5bb3dcb8fb54189e5fc88e649ff3a2313e5383963421114e723b69cd`
  - S4: `fbebd876098ccd792b4d46764201d0c8a80791d2d45dd3da85c59a0499bb145a`
  - S5: `d1ac41f2301b2c0121b4cfe6ddb7bd7b8d71e9e1f7b8fbf9764360c86ebf465c`
- **SHA-256 (first 16 hex digits) of the official in-archive PDFs** [S13]:
  - K001.pdf b6ef87e2fc60c7fd; measuring_log_K001.pdf 827f5ae9eec40ed9
  - K002 118e2c0ba5ed42f8 / 10f28fd84743afdb
  - K003 b68b8ee1fde1f261 / 482a417a559c465a
  - K004 12e2200935856df7 / 4806097aa9577b87
  - K005 73a5b793e7b09380 / bd7cd9725dbd9c11
  - K006 157e355b31baec80 / 624de609ea9b42ca
  - KA01 f21f0ffbda26a1c5 / 942aa35cd3c6bb30
  - KA03 5a6e28873a8009e7 / 5b7469b61a1d838a
  - KA04 3f66eb5cb2df479c / eaf9df99b2aae037
  - KA05 23e4bd7631e36adf / 0883697cb32300da
  - KA06 029aa739b575e446 / 6cfcb24137b45e31
  - KA07 34bd7db344ce7105 / 2d109cc40ec85e42
  - KA08 b89d9630ce74da45 / 862c5bd12f40749b
  - KA09 b0c0f2945f6e4137 / ba7799347b468d78
  - KA15 6954e6549fed0b5f / ce14deb79e8cca48
  - KA16 a32c7a7a5e823472 / 6235f7947fe01072
  - KA22 629b287d6a206174 / 58a20e4ea94cd522
  - KA30 cdf2204bf71188f3 / 6e7d644a059da2cb
  - KB23 3cd0dccc39376adc / 0755f17cd1507777
  - KB24 9ae70efbec7cc14a / e872be4b4b6bc7ff
  - KB27 76329cae4521be08 / 73140c181b4dcae6
  - KI01 ccc94de46dc35de1 / c0036ff0a77ce088
  - KI03 9faa34f64d9ba359 / b8710a7ce003697d
  - KI04 89d141542651a64c / 55018d7406a006a8
  - KI05 6624cc0cdd923a1f / 43cf9c053fe29416
  - KI07 f2cb96109dce1e5a / d397ece2c645494c
  - KI08 6f5502ea5642ad72 / bf1a9d9318b157b0
  - KI14 61c6da9af925d5a6 / 1546d8e6536d0101
  - KI16 ca3588d7d5583af8 / 8002dcd777684a2c
  - KI17 7b4efe0291ddc57c / b97c137076d03994
  - KI18 39e36b4d110a3fe2 / 70732989af77cf38
  - KI21 8a674661919f3e2b / 3d812ed331cc5237
