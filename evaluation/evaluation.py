import argparse
import os
import sys
import glob
import pathlib
import wfdb
import numpy as np
import subprocess
import pandas as pd
import wfdb.processing

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wfdb-dir', type=str, required=True, help='Path to the WFDB directory')
    parser.add_argument('--output-dir', type=str, required=True, help='Path to the output directory')
    parser.add_argument('--qrs-detector', type=str, required=True, help='Path to the qrs detector')
    parser.add_argument('--csv-report', action='store_true', help='Save report to CSV file')

    args = parser.parse_args()

    script_dir = pathlib.Path(__file__).parent.resolve()

    wfdb_dir = os.path.abspath(args.wfdb_dir)
    output_dir = os.path.abspath(args.output_dir)
    qrs_detector_path = os.path.abspath(args.qrs_detector)

    # Validate that the path is a directory
    if not os.path.isdir(wfdb_dir):
        print(f"Error: '{wfdb_dir}' is not a valid directory.")
        sys.exit(1)

    # Validate that the path is a file
    if not os.path.isfile(qrs_detector_path):
        print(f"Error: '{qrs_detector_path}' qrs detector doesn't exist.")
        sys.exit(1)

    wfdb_dir_name = os.path.basename(wfdb_dir)

    qrs_dir_name = wfdb_dir_name
    qrs_dir = os.path.join(output_dir, qrs_dir_name)

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        print(f"Output directory '{output_dir}' does not exist. Creating it.")
        os.makedirs(output_dir, exist_ok=True)

    # Create QRS directory if it doesn't exist
    if not os.path.exists(qrs_dir):
        print(f"QRS directory '{qrs_dir}' does not exist. Creating it.")
        os.makedirs(qrs_dir, exist_ok=True)

    # Get sorted WFDB files list
    wfdb_files_list = sorted(glob.glob(os.path.join(args.wfdb_dir, '*.hea')))

    # Create input files
    for wfdb_file in wfdb_files_list:
        in_file_name = pathlib.Path(wfdb_file).stem + '.in'
        in_file = os.path.join(qrs_dir, in_file_name)

        # Check if the input file exists
        if not os.path.exists(in_file):
            wfdb_record_name = pathlib.Path(wfdb_file).with_suffix('')
            wfdb_record = wfdb.rdrecord(wfdb_record_name, channels=[0], physical=False)
            np.savetxt(in_file, wfdb_record.d_signal, fmt='%d')

    # Get sorted input files list
    in_files_list = sorted(glob.glob(os.path.join(qrs_dir, '*.in')))

    # Process input files with QRS detector
    for in_file in in_files_list:
        out_file = pathlib.Path(in_file).with_suffix('.out')

        # Check if the output file exists
        if not os.path.exists(out_file):
            subprocess.run([args.qrs_detector, in_file, out_file])

    # Get sorted list of output files
    out_files_list = sorted(glob.glob(os.path.join(qrs_dir, '*.out')))

    # Create annotations
    os.chdir(qrs_dir)
    for out_file in out_files_list:
        out_file_values = np.loadtxt(out_file)
        qrs_file = pathlib.Path(out_file).with_suffix('.qrs')

        # Check if qrs file exists
        if not os.path.exists(qrs_file):
            annotation_name = pathlib.Path(qrs_file).stem
            qrs_indices = np.where(out_file_values == 1)[0]
            qrs_symbols = ['N'] * len(qrs_indices)
            wfdb.wrann(annotation_name, 'qrs', qrs_indices, qrs_symbols)

    # Go to the script directory
    os.chdir(script_dir)

    # Get sorted list of qrs files
    qrs_files_list = sorted(glob.glob(os.path.join(qrs_dir, '*.qrs')))

    # Compare detected QRS complexes
    cmp_data_list = []

    for in_file in in_files_list:
        record_name = pathlib.Path(in_file).stem
        ref_ann_path = os.path.join(wfdb_dir, record_name + '.atr')
        test_ann_path = os.path.join(qrs_dir, record_name + '.qrs')

        if os.path.exists(ref_ann_path) and os.path.exists(test_ann_path):
            ref_ann_name = str(pathlib.Path(ref_ann_path).with_suffix(''))
            test_ann_name = str(pathlib.Path(test_ann_path).with_suffix(''))

            ref_ann = wfdb.rdann(ref_ann_name, 'atr')
            test_ann = wfdb.rdann(test_ann_name, 'qrs')

            cmp = wfdb.processing.compare_annotations(ref_sample=ref_ann.sample,
                                                        test_sample=test_ann.sample,
                                                        window_width=int(0.1 * 360))

            sensitivity = round(cmp.sensitivity * 100, 2)
            predictivity = round(cmp.positive_predictivity * 100, 2)

            cmp_data = {
                "Record": record_name,
                "Sensitivity": sensitivity,
                "Predictivity": predictivity
            }

            cmp_data_list.append(cmp_data)

    df = pd.DataFrame(cmp_data_list)
    if (args.csv_report):
        report_file_path = os.path.join(qrs_dir, 'report.csv')
        df.to_csv(report_file_path, index=False)
    print(df)

if __name__ == "__main__":
    main()
