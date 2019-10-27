# lecture_punctuator.py
# Author: Ragy Morkos

#################################################################################

import sys
import os
import re
import string

#################################################################################

def make_new_directory(new_directory_name):
    current_directory = os.getcwd()
    new_directory = current_directory + "/" + new_directory_name
    while os.path.isdir(new_directory):
        new_directory += new_directory_name[-1]
    os.makedirs(new_directory)
    return new_directory

#################################################################################

def convert_to_srt(filename):
    new_filename = filename[:-3] + "srt"
    os.system("ffmpeg -i \"" + filename + "\" \"" + new_filename + "\"")
    os.system("rm \"" + filename + "\"")
    return new_filename

#################################################################################

# Adapted from https://gist.github.com/nimatrueway/4589700f49c691e5413c5b2df4d02f4f
def fix_srt_overlap(filename):
    timeFramePattern = re.compile("(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)")

    class Subtitle:
        def __init__(self, idx, fromTime, toTime, text):
            self.idx = idx
            self.fromTime = fromTime
            self.toTime = toTime
            self.text = text

    def getDuration(parts):
        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2])
        millisecond = int(parts[3])
        return (hour * 3600000000000) + (minute * 60000000000) + (second * 1000000000) + (millisecond * 1000000)

    def printDuration(duration):
        hour = duration / 3600000000000
        duration -= hour * 3600000000000
        minute = duration / 60000000000
        duration -= minute * 60000000000
        second = duration / 1000000000
        duration -= second * 1000000000
        millisecond = duration / 1000000
        return "%02d:%02d:%02d,%03d" % (hour, minute, second, millisecond)

    def readOneSubtitle(i, inputt):
        if i >= len(inputt):
            return i, None

        # read idx
        idx = inputt[i]
        i += 1
        if not idx:
            return i, None
        idx = int(idx)
        
        # read timing
        if i >= len(inputt):
            return None
        timing = inputt[i]
        i += 1
        timing = timeFramePattern.findall(timing)
        if not timing:
            return i, None
        timing = timing[0]
        fromTime = getDuration(timing[:4])
        toTime = getDuration(timing[4:])

        # read content
        j = i
        while j < len(inputt):
            if len(inputt[j]) == 0:
                j += 1
            else:
                break
        
        if j >= len(inputt):
            return i, None
        if inputt[j].isdigit():
            return readOneSubtitle(j, inputt)

        content = inputt[i]
        i += 1
        if not content:
            return None
        content += "\n"
        while i < len(inputt):
            scanned = inputt[i]
            i += 1
            if not scanned:
                break
            content += scanned + "\n"
        
        return i, Subtitle(idx, fromTime, toTime, content)

    def writeOneSubtitle(file, subtitle, idx):
        file.write(str(idx[0]) + "\n" + printDuration(subtitle.fromTime) + " --> " + printDuration(subtitle.toTime) + "\n" + subtitle.text + "\n\n")
        idx[0] += 1

    old_name = filename + ".old"
    os.rename(filename, old_name)
    filee = open(old_name, "r")
    s = ""
    
    for linee in filee:
        line = linee.strip()
        if line:
            if line.isdigit():
                s += "\n"
            s += line + "\n"
    
    if s[0] == "\n":
        s = s[1:]
    
    with open(filename, "w") as filee:
        filee.write(s)
    
    newFilePath = filename + ".fixed"
    with open(filename, "r") as f:
       inputt = f.readlines()
    inputt = [x.strip() for x in inputt]

    newFile = open(newFilePath, "w")
    newIdx = [1]
    lastSubtitle = None
    i = 0
    while True:
        i, subtitle = readOneSubtitle(i, inputt)
        if lastSubtitle:
            if subtitle:
                subtitle.text = subtitle.text.strip()
                if len(subtitle.text) == 0: # skip over empty subtitles
                    continue
                
                # skip over super-short subtitles that basically contain what their previous subtitle contains, and just prolong previous subtitle
                if (subtitle.toTime - subtitle.fromTime < 1000000 * 150) and (subtitle.text in lastSubtitle.text):
                    lastSubtitle.toTime = subtitle.toTime
                    continue
                
                # if first-line of current subtitle is repeating last-line of previous-subtitle remove it
                currentLines = subtitle.text.split("\n")
                currentLines = [x for x in currentLines if x != ""]
                lastLines = lastSubtitle.text.split("\n")
                lastLines = [x for x in lastLines if x != ""]
                if currentLines[0] == lastLines[-1]:
                    subtitle.text = "\n".join(currentLines[1:])

                # if first-line of current subtitle is repeating last-line of previous-subtitle remove it
                if subtitle.fromTime < lastSubtitle.toTime:
                    lastSubtitle.toTime = subtitle.fromTime - 1000000

            writeOneSubtitle(newFile, lastSubtitle, newIdx)

        if not subtitle:
            break

        lastSubtitle = subtitle

    os.rename(filename, filename + ".bak")
    os.rename(newFilePath, filename)

    filee.close()
    newFile.close()

    os.system("rm \"" + filename + ".bak\"")
    os.system("rm \"" + old_name + "\"")

#################################################################################

# function that takes as input directory with trascripts in srt format and converts them to YouTube format
def convert_to_youtube(filename):
    with open(filename, "r") as f:
        s = ""
        for linee in f:
            line = linee.strip()
            if "-->" in line:
                s += line[:8] + " "
            elif line and not line.isdigit():
                s += (line + "\n")
    os.system("rm \"" + filename + "\"")
    with open(filename, "w") as f:
        f.write(s)

#################################################################################

def remove_timecodes(timecoded_filename, nontimecoded_filename):
    with open(timecoded_filename, "r") as f_original, open(nontimecoded_filename, "w") as f:
        s = ""
        for line in f_original:
            s += " ".join(line.strip().split()[1:]) + " "
        s = s.strip()
        f.write(s)

#################################################################################

def restore_timings(timecoded_file, punctuated_filee):
    with open(timecoded_file, "r") as original_file, open(punctuated_filee, "r") as punctuated_file:
        punctuated = punctuated_file.read().strip().split()
        result = ""
        counter = 0
        for line in original_file:
            original = line.strip().split()
            result += original[0]
            wasPreviousQuestionMark = False
            for i in range(1, len(original)):
                if counter < len(punctuated):
                    if punctuated[counter] == "i":
                        punctuated[counter] = "I"
                    
                    if counter + 2 < len(punctuated) and punctuated[counter + 1] == "I.":
                        if punctuated[counter] == "and":
                            punctuated[counter + 1] = "I"
                            punctuated[counter + 2] = punctuated[counter + 2].lower()
                        else:
                            punctuated[counter] += "."
                            punctuated[counter + 1] = "I"
                                
                    punctuated[counter] = string.replace(punctuated[counter], "'S", "'s")
                    punctuated[counter] = string.replace(punctuated[counter], "'L", "'l")
                    punctuated[counter] = string.replace(punctuated[counter], "'R", "'r'")
                    punctuated[counter] = string.replace(punctuated[counter], "'M", "'m")
                    punctuated[counter] = string.replace(punctuated[counter], "java", "Java")
                    punctuated[counter] = string.replace(punctuated[counter], "alice", "Alice")
                    punctuated[counter] = string.replace(punctuated[counter], "bob", "Bob")
                    punctuated[counter] = string.replace(punctuated[counter], "princeton", "Princeton")
                    if wasPreviousQuestionMark:
                        punctuated[counter] = punctuated[counter].title()
                    if punctuated[counter][-1] == "?":
                        wasPreviousQuestionMark = True
                    result += " " + punctuated[counter]
                    counter += 1
                else:
                    break
            result += "\n"
        if result[-2] != ".":
            result = result.strip()
            result += ".\n"
    os.system("rm \"" + punctuated_filee + "\"")
    with open(punctuated_filee, "w") as timed_file:
        timed_file.write(result)

#################################################################################

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise BaseException("Please input a YouTube link.")
    if len(sys.argv) > 2:
        raise BaseException("Please input only one YouTub link.")

    # make two temporary directories for subtitle processing
    temp_directory = make_new_directory("temp")
    temp_directory_2 = make_new_directory("temp_2")

    # make final directory for transcripts
    final_directory = make_new_directory("transcripts")

    # download subtitle/subtitles to temporary directory
    os.system("youtube-dl --ignore-errors --write-auto-sub --skip-download -o \"" + temp_directory + "/%(title)s_%(id)s.%(ext)s\" " + sys.argv[1])

    for filename in os.listdir(temp_directory):
        full_filename = os.path.join(temp_directory, filename)
        
        full_filename = convert_to_srt(full_filename)
        fix_srt_overlap(full_filename)
        convert_to_youtube(full_filename)

        nontimecoded_filename = os.path.join(temp_directory_2, filename)
        remove_timecodes(full_filename, nontimecoded_filename)
        
        path = os.path.dirname(os.path.realpath(__file__))
        neural_network = os.path.join(path, "Neural_Network_Trained_on_Udacity_Transcripts.pcl")
        punctuator = os.path.join(path, "punctuator.py")
        convert_to_readable = os.path.join(path, "convert_to_readable.py")

        punctuated_filename = os.path.join(final_directory, filename[:-3] + "srt")

        os.system("cat \"" + nontimecoded_filename + "\" | python \"" + punctuator + "\" \"" + neural_network + "\" \"" + punctuated_filename + "\"")

        os.system("python \"" + convert_to_readable + "\" \"" + punctuated_filename + "\" \"" + punctuated_filename + "1\"")
        os.system("rm \"" + punctuated_filename + "\"")
        os.rename(punctuated_filename + "1", punctuated_filename)
        os.system("rm \"" + nontimecoded_filename + "\"")

        restore_timings(full_filename, punctuated_filename)

        os.system("rm \"" + full_filename + "\"")

    os.system("rm -r \"" + temp_directory + "\"")
    os.system("rm -r \"" + temp_directory_2 + "\"")
