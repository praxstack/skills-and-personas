// Read by `npx remotion render|still|studio`. The skill's render script passes the same values as flags.
import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg'); // jpeg frames render faster than png
Config.setJpegQuality(92);
Config.setCodec('h264');
Config.setPixelFormat('yuv420p');
Config.setColorSpace('bt709'); // without it Remotion writes full-range yuvj420p even with yuv420p set
Config.setCrf(18);
Config.setMuted(true); // the voice, music and effects are mixed later by mix.py
Config.setOverwriteOutput(true);
