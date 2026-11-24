"""
Job = the processing run of one video (1 video <-> 1 job, so job_id == video_id).
Its status lives in the video hash in Redis (see models/video.py).
"""
import enum


class JobStatus(str, enum.Enum):
    preparing = "preparing"          # probing the file / building the chunk list
    downloading = "downloading"      # YouTube download in progress
    processing = "processing"        # chunks are being censored
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


ACTIVE_STATUSES = (JobStatus.preparing, JobStatus.downloading, JobStatus.processing)
