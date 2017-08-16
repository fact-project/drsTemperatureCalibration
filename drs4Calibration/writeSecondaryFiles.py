import subprocess as sp
import pandas as pd
import numpy as np
import h5py
import yaml
import click
import os
from scipy.stats import chisquare as chi2

from tqdm import tqdm
from astropy.io import fits

from fact.credentials import create_factdb_engine

from drsTemperatureCalibration.constants import NRCHID, NRCELL
from drsTemperatureCalibration.tools import safety_stuff, check_file_match


@click.command()
@click.argument('drs_file_path',
                default="/net/big-tank/POOL/projects/fact/drs_temp_calib_data/" +
                        "calibration/calculation/drsData.h5",
                type=click.Path(exists=True))
@click.argument('fit_file_path',
                default="/net/big-tank/POOL/projects/fact/drs_temp_calib_data/" +
                        "calibration/calculation/drsFitParameter.fits",
                type=click.Path(exists=True))
@click.argument('interval_file_path',
                default="/net/big-tank/POOL/projects/fact/drs_temp_calib_data/" +
                        "calibration/calculation/intervalIndices.h5",
                type=click.Path(exists=True))
@click.argument('interval_array',
                default=[1, 2, 3])
@click.argument('store_file_path',
                default="/net/big-tank/POOL/projects/fact/drs_temp_calib_data/" +
                        "calibration/validating/residuals/drsResiduals.h5",
                type=click.Path(exists=False))
@click.argument('drs_temp_calib_config',
                default="/home/fschulz/git/drsTemperatureCalibration/drsTemperatureCalibration/" +
                        "drsTempCalibConfig.yaml",
                type=click.Path(exists=True))
###############################################################################
def residum_of_all_cells(drs_file_path, fit_file_path,
                         interval_file_path, interval_array,
                         store_file_path, drs_temp_calib_config):
    # TODO add stuff
    '''

        Args:
            drs_file_path (str):
                Full path to the sourceParameter file with the extension '.h5'
            fit_file_path (str):
                Full path to the fit-value-file with the extension '.fits'
            interval_array (int-array):
                (Sorted) Array of ints/numbers of intervals for analysis
            store_file_path (str):
                Full path to the store-file with the extension '.h5'
            drs_temp_calib_config (str):
                Path to the drsCalibrationConfig-file with the extension '.yaml'
    '''

    # TODO check safety stuff. maybe remove
    safety_stuff(store_file_path)

    # Cecking wether the intervalIndices and the fitvalues are based on the given drsData
    check_file_match(drs_file_path,
                     interval_file_path=interval_file_path,
                     fit_file_path=fit_file_path)

    with h5py.File(drs_file_path, 'r') as data_source:
        source_creation_date = data_source.attrs['CreationDate']

    with h5py.File(store_file_path) as store:
        store.clear()
        store.attrs["SCDate"] = source_creation_date

    with open(drs_temp_calib_config) as calbConfig:
        config = yaml.safe_load(calbConfig)

    drs_value_types = config["drsValueTypes"]

    NRCALIBVALUES = NRCHID*NRCELL

    for interval_nr in interval_array:
        groupname = "Interval"+str(interval_nr)
        with h5py.File(interval_file_path, 'r') as interval_source:
            data = interval_source[groupname]
            low_limit = data.attrs["LowLimit"]
            upp_limit = data.attrs["UppLimit"]
            interval_indices = np.array(data["IntervalIndices"])
        with h5py.File(store_file_path) as store:
            drs_group = store.create_group(groupname)
            drs_group.attrs["LowLimit"] = low_limit
            drs_group.attrs["UppLimit"] = upp_limit
        for drs_value_type in drs_value_types:
            print("Loading ...", drs_value_type, " : ",  groupname)
            with h5py.File(drs_file_path, 'r') as data_source:
                temp = np.array(data_source["Temp"+drs_value_type][interval_indices, :])
                drs_value = np.array(data_source[drs_value_type+"Mean"][interval_indices, :])

            with fits.open(fit_file_path, ignoremissing=True, ignore_missing_end=True) as fit_values_tab:
                data = fit_values_tab[interval_nr].data

                slope = data[drs_value_type+"Slope"][0]
                offset = data[drs_value_type+"Offset"][0]

            store = h5py.File(store_file_path)
            store[groupname].create_dataset(drs_value_type+"Residuals",
                                            (drs_value.shape[0], NRCALIBVALUES),
                                            maxshape=(drs_value.shape[0], NRCALIBVALUES),
                                            compression="gzip",
                                            compression_opts=9,
                                            fletcher32=True
                                            )

            for date in tqdm(range(drs_value.shape[0])):
                temp_date = np.repeat(temp[date], 9*NRCELL)
                drs_value_date = drs_value[date]

                model_value = slope*temp_date + offset
                drs_type_residuen_date = drs_value_date - model_value

                data = store[groupname][drs_value_type+"Residuals"]
                data[date] = drs_type_residuen_date
            store.close()

    # add creationDate to h5 file
    creation_date_str = pd.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with h5py.File(store_file_path) as store:
        store.attrs['CreationDate'] = creation_date_str


@click.command()
@click.argument('drs_file_path',
                default="/net/big-tank/POOL/projects/fact/drs_temp_calib_data/" +
                        "calibration/calculation/drsData.h5",
                type=click.Path(exists=True))
@click.argument('fit_file_path',
                default="/net/big-tank/POOL/projects/fact/drs_temp_calib_data/" +
                        "calibration/calculation/drsFitParameter.fits",
                type=click.Path(exists=True))
@click.argument('interval_file_path',
                default="/net/big-tank/POOL/projects/fact/drs_temp_calib_data/" +
                        "calibration/calculation/intervalIndices.h5",
                type=click.Path(exists=True))
@click.argument('interval_array',
                default=[1, 2, 3])
@click.argument('store_file_path',
                default="/net/big-tank/POOL/projects/fact/drs_temp_calib_data/" +
                        "calibration/validating/chiSquare/drsChiSquare_new.h5",
                type=click.Path(exists=False))
@click.argument('drs_temp_calib_config',
                default="/home/fschulz/git/drsTemperatureCalibration/drsTemperatureCalibration/" +
                        "drsTempCalibConfig.yaml",
                type=click.Path(exists=True))
###############################################################################
def chisquare_of_all_cells(drs_file_path, fit_file_path,
                           interval_file_path, interval_array,
                           store_file_path, drs_temp_calib_config):
    # TODO add stuff
    '''

        Args:
            drs_file_path (str):
                Full path to the sourceParameter file with the extension '.h5'
            fit_file_path (str):
                Full path to the fit-value-file with the extension '.fits'
            interval_array (int-array):
                (Sorted) Array of ints/numbers of intervals for analysis
            store_file_path (str):
                Full path to the store-file with the extension '.h5'
            drs_temp_calib_config (str):
                Path to the drsCalibrationConfig-file with the extension '.yaml'
    '''

    # TODO check safety stuff. maybe remove
    safety_stuff(store_file_path)

    # Cecking wether the intervalIndices and the fitvalues are based on the given drsData
    check_file_match(drs_file_path,
                     interval_file_path=interval_file_path,
                     fit_file_path=fit_file_path)

    with h5py.File(drs_file_path, 'r') as data_source:
        source_creation_date = data_source.attrs['CreationDate']

    with h5py.File(store_file_path) as store:
        store.clear()
        store.attrs["SCDate"] = source_creation_date

    with open(drs_temp_calib_config) as calbConfig:
        config = yaml.safe_load(calbConfig)

    drs_value_types = config["drsValueTypes"]

    NRCALIBVALUES = NRCHID*NRCELL

    for interval_nr in interval_array:
        groupname = "Interval"+str(interval_nr)
        with h5py.File(interval_file_path, 'r') as interval_source:
            data = interval_source[groupname]
            low_limit = data.attrs["LowLimit"]
            upp_limit = data.attrs["UppLimit"]
            interval_indices = np.array(data["IntervalIndices"])
        with h5py.File(store_file_path) as store:
            drs_group = store.create_group(groupname)
            drs_group.attrs["LowLimit"] = low_limit
            drs_group.attrs["UppLimit"] = upp_limit

        for drs_value_type in drs_value_types:
            print("Loading ...", drs_value_type, " : ",  groupname)
            with h5py.File(interval_file_path, 'r') as interval_source:
                data = interval_source[groupname]
                mask = np.array(data[drs_value_type+"Mask"])

            with h5py.File(drs_file_path, 'r') as data_source:
                temp_array = data_source["Temp"+drs_value_type][interval_indices, :]
                drs_value = data_source[drs_value_type+"Mean"][interval_indices, :]

            with fits.open(fit_file_path, ignoremissing=True, ignore_missing_end=True) as fit_values_tab:
                data = fit_values_tab[interval_nr].data

                slope = data[drs_value_type+"Slope"][0]
                offset = data[drs_value_type+"Offset"][0]

            store = h5py.File(store_file_path)
            store[groupname].create_dataset(drs_value_type+"Chi2",
                                            (NRCALIBVALUES, ),
                                            compression="gzip",
                                            compression_opts=9,
                                            fletcher32=True
                                            )
            store[groupname].create_dataset(drs_value_type+"P",
                                            (NRCALIBVALUES, ),
                                            compression="gzip",
                                            compression_opts=9,
                                            fletcher32=True
                                            )

            for chid in tqdm(range(NRCHID)):
                temp_chid = temp_array[:, int(chid/9)]
                for cell in range(NRCELL):
                    submask = mask[:, chid*NRCELL+cell]
                    temp_cell = temp_chid[submask]
                    drs_value_cell = drs_value[:, chid*NRCELL+cell][submask]
                    slope_cell = slope[chid*NRCELL+cell]
                    offset_cell = offset[chid*NRCELL+cell]

                    model_value = slope_cell*temp_cell + offset_cell

                    drs_type_chi2_cell, drs_type_p_cell = chi2(model_value,
                                                               f_exp=drs_value_cell)

                    data = store[groupname][drs_value_type+"Chi2"]
                    data[chid*NRCELL+cell] = drs_type_chi2_cell
                    data = store[groupname][drs_value_type+"P"]
                    data[chid*NRCELL+cell] = drs_type_p_cell
            store.close()

    # add creationDate to h5 file
    creation_date_str = pd.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with h5py.File(store_file_path) as store:
        store.attrs['CreationDate'] = creation_date_str


@click.command()
@click.argument('drs_file_list_doc_path',
                default=("/net/big-tank/POOL/projects/fact/drs_temp_calib_data/" +
                         "calibration/drsSourceCollection/drsPedestalFiles.txt"),
                type=click.Path(exists=True))
###############################################################################
def pedestal_files_list(drs_file_list_doc_path):
    def filename(row):
        return os.path.join(
            str(row.date.year),
            "{:02d}".format(row.date.month),
            "{:02d}".format(row.date.day),
            "{}_{:03d}.fits.fz".format(row.fNight, row.fRunID),
        )

    db_table = pd.read_sql(  # TODO maybe query start_date an end_date with fNight
                    "RunInfo",
                    create_factdb_engine(),
                    columns=[
                        "fNight", "fRunID",
                        "fRunTypeKey", "fDrsStep",
                        "fNumEvents", "fBiasVoltageMedian"])
    selected_drs_infos = db_table.query("fRunTypeKey == 2 &" +
                                        "fDrsStep != fDrsStep &" +
                                        "fBiasVoltageMedian != fBiasVoltageMedian").copy()

    selected_drs_infos["date"] = pd.to_datetime(selected_drs_infos.fNight.astype(str), format="%Y%m%d")

    pedestalFiles = selected_drs_infos.apply(filename, axis=1).tolist()
    pd.DataFrame(pedestalFiles).to_csv(drs_file_list_doc_path, index=False, header=False)


@click.command()
@click.argument('source_folder_path',
                default=("/net/big-tank/POOL/projects/fact/" +
                         "drs_temp_calib_data/"),
                type=click.Path(exists=True))
@click.argument('store_folder_path',
                default=("/net/big-tank/POOL/projects/fact/" +
                         "drs_temp_calib_data/calibration/validating/noise/"),
                type=click.Path(exists=True))
@click.argument('facttools_file_path',
                default=("/home/fschulz/git/fact-tools/" +
                         "target/fact-tools-0.18.0.jar"),
                type=click.Path(exists=True))
@click.argument('facttools_xml_path',
                default=("/home/fschulz/git/fact-tools/" +
                         "examples/studies/drsTemperatureCalibrationCheck.xml"),
                type=click.Path(exists=True))
@click.argument('fitparameter_file_path',
                default=("/home/fschulz/git/fact-tools" +
                         "/src/main/resources/default/drsFitParameter.fits"),
                type=click.Path(exists=True))
@click.argument('start_date',
                default="2016-01-01")
@click.argument('end_date',
                default="2017-01-01")
@click.argument('freq',
                default="D")
###############################################################################
def drs_pedestal_run_noise(source_folder_path, store_folder_path,
                           facttools_file_path, facttools_xml_path,
                           fitparameter_file_path,
                           start_date, end_date, freq="D"):
    print("Loading Database ...")
    # TODO maybe query start_date an end_date with fNight
    db_table = pd.read_sql(
                    "RunInfo",
                    create_factdb_engine(),
                    columns=[
                        "fNight", "fRunID",
                        "fRunTypeKey", "fDrsStep",
                        "fNumEvents", "fBiasVoltageMedian"])

    # loop over the start_date to end_date interval
    for date in tqdm(pd.date_range(start=start_date, end=end_date, freq=freq)):

        date_str = date.strftime('%Y%m%d')

        date_path = date.strftime('%Y/%m/%d/')
        pre_aux_path = source_folder_path+"aux/"+date_path
        pre_drs_path = source_folder_path+"raw/"+date_path

        temp_file = (pre_aux_path+date_str+".FAD_CONTROL_TEMPERATURE.fits")

        # skip calculation if no temperatur file exist
        if(not os.path.isfile(temp_file)):
            print("Date: ", date_str, " has no temp file")  # TODO maybe log
            continue

        selected_drs_infos = db_table.query("fNight =="+str(date_str)+"&" +
                                            "fRunTypeKey == 2 &" +
                                            "fDrsStep == 2 &" +
                                            "fNumEvents == 1000").copy()

        selected_drs_infos["date"] = pd.to_datetime(
                                        selected_drs_infos.fNight.astype(str),
                                        format="%Y%m%d")

        drs_run_id_list = selected_drs_infos["fRunID"].tolist()
        if(len(drs_run_id_list) == 0):
            print("Date: ", date_str, " no drs files token")  # TODO maybe log
            continue

        # just use one drs-Run for the calculations
        # to afford larger temperature differences
        # (all pedestal-runs follow right after
        # the drs-run taking, so there are just small
        # temperature differences)
        # so we take the drs-Run of the middle of the night
        # keep im mind other influences in time can now appear
        # and distort the results

        drs_run_index = int(len(drs_run_id_list)/2)
        drs_run_id = drs_run_id_list[drs_run_index]
        drs_file = (pre_drs_path+date_str +
                    "_"+str("{:03d}".format(drs_run_id))+".drs.fits.gz")

        # skip calculation if no drs file exist
        if(not os.path.isfile(drs_file)):
            print("Date: ", date_str, " has no drs-file", drs_file)  # TODO maybe log, maybe use other one
            continue

        # fDrsStep == NaN and fBiasVoltageMedian == NaN dosent work
        selected_drs_infos = db_table.query(
                                "fNight =="+str(date_str)+"&" +
                                "fRunTypeKey == 2 &" +
                                "fDrsStep != fDrsStep &" +
                                "fBiasVoltageMedian != fBiasVoltageMedian"
                             ).copy()

        selected_drs_infos["date"] = pd.to_datetime(selected_drs_infos.fNight.astype(str), format="%Y%m%d")
        pedestel_run_id_list = selected_drs_infos["fRunID"].tolist()

        used_pedestel_run_ids = []
        pedestel_run_file_list = []
        for run_id in pedestel_run_id_list:
            pedestelrun_filename = (pre_drs_path+date_str+"_"+str("{:03d}".format(run_id))+".fits.fz")
            if(os.path.isfile(pedestelrun_filename)):
                used_pedestel_run_ids.append(run_id)
                pedestel_run_file_list.append(pedestelrun_filename)
            else:
                print(pedestelrun_filename, " not found")

        if(used_pedestel_run_ids == []):
            continue

        with fits.open(temp_file) as tempTab:
            timeList = np.array(tempTab[1].data['Time'])
            temp_list = np.array(tempTab[1].data['temp'])
            tempDatetime = pd.to_datetime(timeList * 24 * 3600 * 1e9)

        with fits.open(drs_file) as drsTab:
            drsStart = pd.to_datetime(drsTab[1].header["DATE-OBS"])
            drsEnd = pd.to_datetime(drsTab[1].header["DATE-END"])
            # mean ignore patches -->, axis=0 <--
            drsTempMean = np.mean(temp_list[np.where((tempDatetime > drsStart) & (tempDatetime < drsEnd))])

        store_folder_path_tmp = store_folder_path+date_str+"/"
        if not os.path.exists(store_folder_path_tmp):
            os.makedirs(store_folder_path_tmp)
        tempDiffList = []
        for run_index in range(len(pedestel_run_file_list)):
            run_file = pedestel_run_file_list[run_index]
            run_id = used_pedestel_run_ids[run_index]

            with fits.open(run_file) as run_tab:
                run_start = run_tab[2].header["DATE-OBS"]
                run_end = run_tab[2].header["DATE-END"]

            run_temp = temp_list[np.where((tempDatetime > run_start) & (tempDatetime < run_end))[0]]

            if(len(run_temp) == 0):
                run_temp = temp_list[np.where((tempDatetime < run_start))[0][-1]:
                                     np.where((tempDatetime > run_end))[0][0]+1]

            tempDiffList.append(abs(np.mean(run_temp) - drsTempMean))
            print("run java ", run_index+1, "/", len(pedestel_run_file_list), "for", date_str)
            #continue
            store_file_path = (store_folder_path_tmp+"pedestelNoise_" +
                               date_str+"_{0:03d}".format(run_id)+"_tmp.fits")
            run_fact_tools(facttools_file_path, facttools_xml_path, run_file,
                           store_file_path, drs_file, pre_aux_path,
                           fitparameter_file_path)
        continue
        print("Join Noise.fits of ", date_str)

        drs_calibrated_data_noise = []
        drs_calibrated_data_noise_temp = []

        for run_id in used_pedestel_run_ids:
            print("Add run ID: ", run_id)
            source_file = (store_folder_path_tmp+"pedestelNoise_" +
                           date_str+"_{0:03d}".format(run_id)+"_tmp.fits")
            if(os.path.isfile(source_file)):
                with fits.open(source_file) as noise_tab:
                    drs_calibrated_data_noise.append(
                        noise_tab[1].data["DRSCalibratedDataNoise"].flatten())
                    drs_calibrated_data_noise_temp.append(
                        noise_tab[1].data["DRSCalibratedDataNoise_Temp"].flatten())
                # os.remove(source_file)
        # os.rmdir(store_folder_path_tmp)

        # TODO add run ids
        print("Write Data to Table")
        tbhduNoise = fits.BinTableHDU.from_columns(
                [fits.Column(
                    name="PedestelRunId", format='1E', # format='1I' for int dosent work
                    unit="1", array=used_pedestel_run_ids),
                 fits.Column(
                    name="TempDiff", format='1E',
                    unit="Degree C", array=tempDiffList),
                 fits.Column(
                    name="DrsCalibratedDataNoise", format='PE()',
                    unit="mV", array=drs_calibrated_data_noise),
                 fits.Column(
                    name="DrsCalibratedDataNoiseTemp", format='PE()',
                    unit="mV", array=drs_calibrated_data_noise_temp)])
        tbhduNoise.header.insert("TFIELDS", ("EXTNAME", "NoisePerPixel"), after=True)
        commentStr = ("-")
        tbhduNoise.header.insert("EXTNAME", ("comment", commentStr), after="True")
        tbhduNoise.header.insert("comment", ("Date", date_str, "Date yyyy-mm-dd"), after=True)
        tbhduNoise.header.insert("Date", ("DrsRunId", drs_run_id, "RunID of the based drsrun_file"), after=True)

        store_file_path = store_folder_path+"pedestelNoise_"+date_str+".fits"
        print("Save Table")
        thdulist = fits.HDUList([fits.PrimaryHDU(), tbhduNoise])
        thdulist.writeto(store_file_path, overwrite=True, checksum=True)
        print("Verify Checksum")
        # Open the File verifying the checksum values for all HDUs
        try:
            hdul = fits.open(store_file_path, checksum=True)
            print(hdul["NoisePerPixel"].header)
        except Exception as errInfos:
            errorStr = str(errInfos)
            print(errorStr)


###############################################################################
def run_fact_tools(facttools_file_path, facttools_xml_path, run_file,
                   store_file_path, drs_file, pre_aux_path,
                   fitparameter_file_path):

    # print(facttools_file_path)
    # print(facttools_xml_path)
    # print(run_file)
    # print(store_file_path)
    # print(drs_file)
    # print(pre_aux_path)
    # print(fitparameter_file_path)
    sp.run(["java", "-jar", "{}".format(facttools_file_path),
            "{}".format(facttools_xml_path),
            "-Dinfile=file:{}".format(run_file),
            "-Doutfile=file:{}".format(store_file_path),
            "-Ddrsfile=file:{}".format(drs_file),
            "-DauxFolder=file:{}".format(pre_aux_path),
            "-DfitParameterFile=file:{}".format(fitparameter_file_path),
            "-j8"])


# # TODO FIX Checksum error
# ####################################################################################################
# def temperatureMaxDifferencesPerPatch(store_file_path, source_pre_path, start_date, end_date, freq="D"):
#     print(">> Run 'Temperature: MaxDifferencesPerPatch' <<")
#
#     if(not os.path.isdir(source_pre_path)):
#         print("Folder '", source_pre_path, "' does not exist")
#         sys.exit()
#
#     if(os.path.isfile(store_file_path)):
#         userInput = input("File ’"+str(store_file_path)+"’ allready exist.\n" +
#                           " Type ’y’ to overwrite File\nYour input: ")
#         if(userInput != 'y'):
#             sys.exit()
#
#     elif(not os.path.isdir(store_file_path[0:store_file_path.rfind("/")])):
#         print("Folder '", store_file_path[0:store_file_path.rfind("/")], "' does not exist")
#         sys.exit()
#
#     engine = create_factdb_engine
#     db_table = pd.read_sql("RunInfo", engine, columns=["fNight", "fRunID",
#                                                       "fRunTypeKey", "fDrsStep",
#                                                       "fNumEvents"])
#
#     dateList = []
#     drs_run_id_list = []
#     maxTempDiffList = []
#
#     month_before = 0
#     for date in pd.date_range(start=start_date, end=end_date, freq=freq):
#         if(month_before < date.month):
#             month_before = date.month
#             print("Month: ", date.month)
#         # print("Date: ", date)
#
#         date_path = date.strftime('%Y/%m/%d/')
#         date_str = date.strftime('%Y%m%d')
#
#         temp_file = source_pre_path+"gpfs0/fact/fact-archive/rev_1/aux/"+date_path+date_str+".FAD_CONTROL_TEMPERATURE.fits"
#         drsdate_str = date.strftime('%Y-%m-%d')
#
#         if(os.path.isfile(temp_file)):
#             # print("found temp_file: ", temp_file)
#             with fits.open(temp_file) as tabTemp:
#                 time = tabTemp[1].data["Time"]
#                 datetime = pd.to_datetime(time * 24 * 3600 * 1e9)
#                 temp = tabTemp[1].data["temp"]
#         else:
#             continue
#
#         selected_drs_infos = db_table.query("fNight =="+str(date_str)+"&" +
#                                          "fRunTypeKey == 2 & fDrsStep == 2 & fNumEvents == 1000").copy()
#         totaldrs_run_id_list = selected_drs_infos["fRunID"].tolist()
#
#         drsTemp = None
#         drs_run_idOfTheDay = np.array([])
#         maxTempDiffOfTheDay = np.array([])
#         for drs_run_id in totaldrs_run_id_list:
#             drs_file = (source_pre_path+"gpfs0/fact/fact-archive/rev_1/raw/" +
#                        date_path+date_str+"_"+str("{:03d}".format(drs_run_id))+".drs.fits.gz")
#             if (os.path.isfile(drs_file)):
#                 # print("Use File: ", drs_file)
#                 with fits.open(drs_file) as drsTab:
#                     drsRunStart = pd.to_datetime(drsTab[1].header["DATE-OBS"])
#                     drsRunEnd = pd.to_datetime(drsTab[1].header["DATE-END"])
#
#                 drs_run_idOfTheDay = np.append(drs_run_idOfTheDay, drs_run_id)
#                 drsRunIndices = np.where((datetime > drsRunStart) & (datetime < drsRunEnd))[0]
#                 # check first Drs-Run
#                 if(drsTemp is None):
#                     # Save the Date where a mimimum of one drs-Run was found
#                     dateList.append([drsdate_str])
#                 else:
#                     tempInterval = temp[0:drsRunIndices[0]]
#                     maxTempDiffOfTheDay = np.append(maxTempDiffOfTheDay, np.array(
#                                                     np.amax([
#                                                              np.amax(tempInterval, axis=0) - drsTemp,
#                                                              drsTemp - np.amin(tempInterval, axis=0)
#                                                              ], axis=0)))
#
#                 # Save Drs-Run Temperature
#                 drsTemp = np.mean(temp[drsRunIndices], axis=0)
#                 # cutoff the previous values of datetime and temp
#                 datetime = datetime[drsRunIndices[-1]+1:]
#                 temp = temp[drsRunIndices[-1]+1:]
#
#         if(drsTemp is not None):
#             # append values after last Drs-Run
#             drsTemp = np.mean(temp, axis=0)
#             maxTempDiffOfTheDay = np.append(maxTempDiffOfTheDay, np.array(
#                                             np.amax([
#                                                      np.amax(tempInterval, axis=0) - drsTemp,
#                                                      drsTemp - np.amin(tempInterval, axis=0)
#                                                      ], axis=0)))
#             # append data of the day
#             drs_run_id_list.append(drs_run_idOfTheDay.astype("uint16"))
#             maxTempDiffList.append(maxTempDiffOfTheDay)
#
#     print("Write Data to Table")
#     tbhduTempDiff = fits.BinTableHDU.from_columns(
#             [fits.Column(name="date",        format="10A",
#                          unit="yyyy-mm-dd",  array=dateList),
#              fits.Column(name="drs_run_id",    format="PB()",
#                          unit="1",           array=drs_run_id_list),
#              fits.Column(name="maxTempDiff", format="PE()",
#                          unit="degree C",    array=maxTempDiffList)])
#     tbhduTempDiff.header.insert("TFIELDS", ("EXTNAME", "MaxDrsTempDiffs"), after=True)
#     commentStr = "Maximum of the Temperature difference between two following Drs-Runs"
#     tbhduTempDiff.header.insert("EXTNAME", ("comment", commentStr), after=True)
#
#     print("Save Table")
#     thdulist = fits.HDUList([fits.PrimaryHDU(), tbhduTempDiff])
#     thdulist.writeto(store_file_path, overwrite=True, checksum=True)
#
#     print("Verify Checksum")
#     # Open the File verifying the checksum values for all HDUs
#     try:
#         hdul = fits.open(store_file_path, checksum=True)
#         print(hdul["MaxDrsTempDiffs"].header)
#         print("Passed verifying Checksum")
#     except Exception as errInfos:
#         errorStr = str(errInfos)
#         print(errorStr)
#
#     print(">> Finished 'Temperature: MaxDifferencesPerPatch'")

# source_pre_path="/home/florian/Dokumente/Uni/Master/Masterarbeit/isdcRoot/",
#     sourcePath_="/home/florian/Dokumente/Uni/Master/Masterarbeit/isdcRoot/gpfs0/scratch/schulz/",
#     store_path="/home/florian/Dokumente/Uni/Master/Masterarbeit/isdcRoot/gpfs0/scratch/schulz/",
#     fact_path="/home/florian/Dokumente/Uni/Master/Masterarbeit/FACT/git_fact-tools/",
#     start_date="2016-09-01",
#     end_date="2016-09-01",
#     freq="D")