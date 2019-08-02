The code and example herein are created to help OpenScope proposals to align their stimuli.

Three scripts are used that recycle functions from the Allen Institute Brain Observatory pipeline code.
Users will only need run: create_stimulus_df.py

This script will load two files, a pickle file and a sync.h5 which are from a real pilot for another
OpenScope proposal (explained below). The code will need modifications based on the experimental
uniqueness of your project and is just to be considered a starting point.  All functions, however, are
from the Brain Observatory pipeline.



The experimental pilot was set up such that the stimuli presented were:
60 seconds gray screen which is called movie = -1;
60 seconds stimulus shown only once called movie = 0;
12 movies shown a total of 10 times (trials) called movies [1,12] which are a 30seconds long.

Note that, technically, the grey screen movie is not a "movie" in that no 3D numpy array existed for it. It
was just a pre-blank stimulus.

The code will use both the pickle file and HDF5 file to return a dataframe that is aligned to the imaging
frames (df/f) as the screen frequency was 60Hz and the imaging was at 30Hz (slighlty higher 30Hz in fact).
Note you will see that the first frame (for movie = -1) starts at frame 133. This is because the
imaging starts before the stimulus does by less than 5 seconds. This is one check you can do that your
alignment is correct as you modify the code.


Note, the script takes about 5 or so minutes to run.
