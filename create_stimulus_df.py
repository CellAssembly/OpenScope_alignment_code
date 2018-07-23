import pickle

import numpy as np
import pandas as pd

from dataset import Dataset
from starter_code_for_credit_assignment.Dataset2p import Dataset2p

ASSUMED_DELAY = 0.0351
DELAY_THRESHOLD = 0.001
FIRST_ELEMENT_INDEX = 0
SECOND_ELEMENT_INDEX = 1
SKIP_FIRST_ELEMENT = 1
ROUND_PRECISION = 4
ZERO = 0
ONE = 1
TWO = 2
MIN_BOUND = .03
MAX_BOUND = .04

def calculate_stimulus_alignment(stim_time, valid_twop_vsync_fall):
    print 'calculating stimulus alignment'

    # convert stimulus frames into twop frames
    stimulus_alignment = np.empty(len(stim_time))

    for index in range(len(stim_time)):
        crossings = np.nonzero(np.ediff1d(np.sign(valid_twop_vsync_fall - stim_time[index])) > ZERO)
        try:
            stimulus_alignment[index] = int(crossings[FIRST_ELEMENT_INDEX][FIRST_ELEMENT_INDEX])
        except:
            stimulus_alignment[index] = np.NaN

    return stimulus_alignment


def calculate_valid_twop_vsync_fall(sync_data, sample_frequency):
    ####microscope acquisition frames####
    # get the falling edges of 2p
    twop_vsync_fall = sync_data.get_falling_edges('2p_vsync') / sample_frequency

    if len(twop_vsync_fall) == 0:
        raise ValueError('Error: twop_vsync_fall length is 0, possible invalid, missing, and/or bad data')

    ophys_start = twop_vsync_fall[0]

    # only get data that is beyond the start of the experiment
    valid_twop_vsync_fall = twop_vsync_fall[np.where(twop_vsync_fall > ophys_start)[FIRST_ELEMENT_INDEX]]

    # skip the first element to eliminate the DAQ pulse
    return valid_twop_vsync_fall


def calculate_stim_vsync_fall(sync_data, sample_frequency):
    ####stimulus frames####
    # skip the first element to eliminate the DAQ pulse
    stim_vsync_fall = sync_data.get_falling_edges('stim_vsync')[SKIP_FIRST_ELEMENT:] / sample_frequency

    return stim_vsync_fall


def calculate_delay(sync_data, stim_vsync_fall, sample_frequency):
    print 'calculating delay'

    try:
        # photodiode transitions
        photodiode_rise = sync_data.get_rising_edges('stim_photodiode') / sample_frequency

        ####Find start and stop of stimulus####
        # test and correct for photodiode transition errors
        photodiode_rise_diff = np.ediff1d(photodiode_rise)
        min_short_photodiode_rise = 0.1
        max_short_photodiode_rise = 0.3
        min_medium_photodiode_rise = 0.5
        max_medium_photodiode_rise = 1.5

        # find the short and medium length photodiode rises
        short_rise_indexes = np.where(np.logical_and(photodiode_rise_diff > min_short_photodiode_rise, \
                                                     photodiode_rise_diff < max_short_photodiode_rise))[
            FIRST_ELEMENT_INDEX]
        medium_rise_indexes = np.where(np.logical_and(photodiode_rise_diff > min_medium_photodiode_rise, \
                                                      photodiode_rise_diff < max_medium_photodiode_rise))[
            FIRST_ELEMENT_INDEX]

        short_set = set(short_rise_indexes)

        # iterate through the medium photodiode rise indexes to find the start and stop indexes
        # lookng for three rise pattern
        next_frame = ONE
        start_pattern_index = 2
        end_pattern_index = 3
        ptd_start = None
        ptd_end = None

        for medium_rise_index in medium_rise_indexes:
            if set(range(medium_rise_index - start_pattern_index, medium_rise_index)) <= short_set:
                ptd_start = medium_rise_index + next_frame
            elif set(range(medium_rise_index + next_frame, medium_rise_index + end_pattern_index)) <= short_set:
                ptd_end = medium_rise_index

        # if the photodiode signal exists
        if ptd_start != None and ptd_end != None:
            # check to make sure there are no there are no photodiode errors
            # sometimes two consecutive photodiode events take place close to each other
            # correct this case if it happens
            photodiode_rise_error_threshold = 1.8
            last_frame_index = -1

            # iterate until all of the errors have been corrected
            while any(photodiode_rise_diff[ptd_start:ptd_end] < photodiode_rise_error_threshold):
                error_frames = np.where(photodiode_rise_diff[ptd_start:ptd_end] < \
                                        photodiode_rise_error_threshold)[FIRST_ELEMENT_INDEX] + ptd_start
                # remove the bad photodiode event
                photodiode_rise = np.delete(photodiode_rise, error_frames[last_frame_index])
                ptd_end -= 1
                photodiode_rise_diff = np.ediff1d(photodiode_rise)

            ####Find the delay####
            # calculate monitor delay
            first_pulse = ptd_start
            number_of_photodiode_rises = ptd_end - ptd_start
            half_vsync_fall_events_per_photodiode_rise = 60
            vsync_fall_events_per_photodiode_rise = half_vsync_fall_events_per_photodiode_rise * 2

            delay_rise = np.empty(number_of_photodiode_rises)
            for photodiode_rise_index in range(number_of_photodiode_rises):
                delay_rise[photodiode_rise_index] = photodiode_rise[photodiode_rise_index + first_pulse] - \
                                                    stim_vsync_fall[(
                                                                    photodiode_rise_index * vsync_fall_events_per_photodiode_rise) + \
                                                                    half_vsync_fall_events_per_photodiode_rise]

            # get a single delay value by finding the mean of all of the delays - skip the last
            # element in the array (the end of the experimenet)
            delay = np.mean(delay_rise[:last_frame_index])

            if (delay > DELAY_THRESHOLD or np.isnan(delay)):
                print "Sync error needs to be fixed"
                delay = ASSUMED_DELAY
                print "Using assumed delay:", round(delay, ROUND_PRECISION)

        # assume delay
        else:
            delay = ASSUMED_DELAY
    except Exception as e:
        print e
        print "Process without photodiode signal"
        delay = ASSUMED_DELAY
        print "Assumed delay:", round(delay, ROUND_PRECISION)

    return delay






if __name__=="__main__":

    pkl_file_name = '710536829_389015_20180616_stim.pkl'
    syn_file_name = '710536829_389015_20180616_sync.h5'
    num_movies = 13         # Number of total moives
    trials = [1] + [10]*12  # List with number of trials for every movie. Should be equal of length=num_movies


    # Read the pickle file and call it "pkl"
    file = open(pkl_file_name, 'rb')
    pkl = pickle.load(file)
    file.close()

    # create a Dataset object with the sync file
    sync_data = Dataset(syn_file_name)

    # create Dataset2p object which will be used for the delay
    dset = Dataset2p(syn_file_name)



    sample_frequency = sync_data.meta_data['ni_daq']['counter_output_freq']

    # calculate the valid twop_vsync fall
    valid_twop_vsync_fall = calculate_valid_twop_vsync_fall(sync_data, sample_frequency)

    # get the stim_vsync_fall
    stim_vsync_fall = calculate_stim_vsync_fall(sync_data, sample_frequency)

    # find the delay
    #delay = calculate_delay(sync_data, stim_vsync_fall, sample_frequency)
    delay = dset.display_lag

    # adjust stimulus time with monitor delay
    stim_time = stim_vsync_fall + delay

    # find the alignment
    stimulus_alignment = calculate_stimulus_alignment(stim_time, valid_twop_vsync_fall)




    print "Creating the stim_df:"
    stim_df = pd.DataFrame(index=range(np.sum(trials)), columns=['movie', 'trial', 'start_frame', \
                                                                 'end_frame', 'num_frames'])

    offset = int(pkl['pre_blank_sec'] *pkl['fps'])

    zz = 0
    # For gray-screen pre_blank
    stim_df.ix[zz, 'movie'] = -1
    stim_df.ix[zz, 'trial'] = 0
    stim_df.ix[zz, 'start_frame'] = stimulus_alignment[0]
    stim_df.ix[zz, 'end_frame'] = stimulus_alignment[offset]
    stim_df.ix[zz, 'num_frames'] = stimulus_alignment[offset] - stimulus_alignment[0]
    zz += 1

    for movie in range(num_movies):
        print 'movie:', movie
        movie_frames = pkl['stimuli'][movie]['frame_list']
        stimulus_start_inds = np.where(movie_frames == 0)[0]
        stimulus_end_inds = np.where(movie_frames == np.max(movie_frames))[0]
        for trial in range(trials[movie]):
            tup = (trial, int(stimulus_alignment[stimulus_start_inds[trial * 2] + offset]), \
                   int(stimulus_alignment[stimulus_end_inds[trial * 2 + 1] + 1 + offset]))

            stim_df.ix[zz, 'movie'] = movie
            stim_df.ix[zz, 'trial'] = trial
            stim_df.ix[zz, 'start_frame'] = tup[1]
            stim_df.ix[zz, 'end_frame'] = tup[2]
            stim_df.ix[zz, 'num_frames'] = tup[2] - tup[1]
            zz += 1

    print stim_df