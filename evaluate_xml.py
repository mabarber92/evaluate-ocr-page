from zipfile import ZipFile
import xml.etree.ElementTree as ET
import os
import re
import fastwer
import csv
import statistics

def check_input(input_folder):
    """check input folder has only one file in it and that file is a zip - 
     if it is, return the path to the single zip - if not print error and exit"""
    files = os.listdir(input_folder)
    files.remove("README.md")
    no_files = len(files)
    if no_files == 1:        
        if files[0].split(".")[-1] == "zip":
            return os.path.join(input_folder, files[0])
        else:
            print("ERROR: {} does not contain a zip file".format(input_folder))
            exit()
    else:        
        print("ERROR: {} contains {} files - it should only contain 1 file".format(input_folder, no_files))
        exit()


def unpack_xmlzips(zip_path, out="temp"):
    """Unpack a zip file into the temp folder"""
    file_name = zip_path.split("/")[-1]
    out_path = os.path.join(out, file_name)
    print("Extracting {} into directory {}".format(file_name, out_path))
    
    # Unpack zip into specific temp directory
    with ZipFile(zip_path, "r") as zObject:
        zObject.extractall(path=out_path) 

    # return xml directory for later use
    return out_path

def xml_list_to_text_list(root_list):    
    out_list = []
    for child in root_list:
        out_list.append(child.text)
    return out_list

def lines_text_from_xml(xml_path, filter_region = "MainZone"):
    """parses xml to return a list of strings for comparison"""
    print("Parsing lines from xmls")
    # Parse the xml and get the tree and root
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Using the tree fetch the scheema url
    scheema_url = re.findall(r'{.*}', str(root.findall('.')[0]))[0]
    xml_string = ".//" + scheema_url + "Unicode"
    
    # if filter_region is None - just fetch all of the lines as a list
    if filter_region is None:        
        line_list = xml_list_to_text_list(root.findall(xml_string))

    
    else:
        filter_region = 'structure {{type:{};}}'.format(filter_region)
        print("Filtering to region: {}".format(filter_region))
        reg_xml_string = ".//" + scheema_url + "TextRegion"
        full_xml_string = "./{}TextEquiv/{}Unicode".format(scheema_url, scheema_url)        
        line_list = []
        for region in root.findall(reg_xml_string):
            attribs = region.attrib
            if "custom" in attribs.keys():           
                if attribs['custom'] == filter_region:
                    for child in region:                    
                        line_list_extend = xml_list_to_text_list(child.findall(full_xml_string))
                        line_list.extend(line_list_extend)
    
    return line_list

def calc_cer_wer(eval_lines, test_lines):
    print("Calculating character error rate and word error rate")
    out = []
    cer_list = []
    wer_list = []
    for index, eval_line in enumerate(eval_lines):
        test_line = test_lines[index]
        cer = fastwer.score_sent(test_line, eval_line, char_level=True)
        wer = fastwer.score_sent(test_line, eval_line, char_level=False)
        out.append({"test_line": test_line, "evaluation_line": eval_line, "cer": cer, "wer": wer})
        cer_list.append(cer)
        wer_list.append(wer)
    
    print("Mean cer for all lines is: {}".format(statistics.mean(cer_list)))
    print("Mean wer for all lines is: {}".format(statistics.mean(wer_list)))
    return out
        

def evaluate_from_zips(filter_region="MainZone"):
    """Assumes only one zip file - will only take the first that appears on a listdir"""
    evaluation_path = "./evaluation_xml"
    test_path = "./test_xml"

    evaluation_zip = check_input(evaluation_path)
    test_zip = check_input(test_path)

    # Unpack the zips
    evaluation_temp_path = unpack_xmlzips(evaluation_zip)
    test_temp_path = unpack_xmlzips(test_zip)

    # Take evaluation as a base and use that for comparison with the test
    test_xmls = os.listdir(test_temp_path)

    for file in os.listdir(evaluation_temp_path):
        # Check that we have corresponding xml file names in the two given zips - if we don't skip to the next
        if file == "METS.xml":
            continue
        elif file.split(".")[-1] != "xml":            
            continue
        elif file not in test_xmls:
            print("{} not found in the test_xml - ensure you have matching xml inputs".format(file))
            continue
        # If we find correspond test xml - get the paths, parse and compare
        else:
            eval_path = os.path.join(evaluation_temp_path, file)
            test_path = os.path.join(test_temp_path, file)

            print(eval_path)
            print(test_path)

            # Get the lines

            eval_lines = lines_text_from_xml(eval_path, filter_region=filter_region)
            test_lines = lines_text_from_xml(test_path, filter_region=filter_region)

            # Compare the lines
            dict_list_cer = calc_cer_wer(eval_lines, test_lines)

            # Output a csv
            field_names = dict_list_cer[0].keys()
            with open('out/eval{}.csv'.format(file), 'w', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=field_names)
                writer.writeheader()
                writer.writerows(dict_list_cer)



if __name__ == "__main__":
    evaluate_from_zips()