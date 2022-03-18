"""
Train a diffusion model on videos.
"""

import argparse
import os, sys

from improved_diffusion import dist_util, logger
from improved_diffusion.image_datasets import load_video_data
from improved_diffusion.resample import create_named_schedule_sampler
from improved_diffusion.script_util import (
    video_model_and_diffusion_defaults,
    create_video_model_and_diffusion,
    args_to_dict,
    add_dict_to_argparser,
)
from improved_diffusion.train_util import TrainLoop


if "--unobserve" in sys.argv:
    sys.argv.remove("--unobserve")
    os.environ["WANDB_MODE"] = "dryrun"


def main():
    args = create_argparser().parse_args()

    dist_util.setup_dist()
    logger.configure(config=args)

    logger.log("creating video model and diffusion...")
    model, diffusion = create_video_model_and_diffusion(
        **args_to_dict(args, video_model_and_diffusion_defaults().keys())
    )
    model.to(dist_util.dev())
    schedule_sampler = create_named_schedule_sampler(args.schedule_sampler, diffusion)

    logger.log("creating data loader...")
    data = load_video_data(
        data_path=args.data_path,
        batch_size=args.batch_size,
    )

    logger.log("training...")
    TrainLoop(
        model=model,
        diffusion=diffusion,
        data=data,
        batch_size=args.batch_size,
        microbatch=args.microbatch,
        lr=args.lr,
        ema_rate=args.ema_rate,
        log_interval=args.log_interval,
        sample_interval=args.sample_interval,
        save_interval=args.save_interval,
        resume_checkpoint=args.resume_checkpoint,
        use_fp16=args.use_fp16,
        fp16_scale_growth=args.fp16_scale_growth,
        schedule_sampler=schedule_sampler,
        weight_decay=args.weight_decay,
        lr_anneal_steps=args.lr_anneal_steps,
        do_inefficient_marg=args.do_inefficient_marg,
        n_valid_batches=args.n_valid_batches,
        n_valid_repeats=args.n_valid_repeats,
        max_frames=args.max_frames,
    ).run_loop()


def create_argparser():
    defaults = dict(
        data_path="",
        schedule_sampler="uniform",
        lr=1e-4,
        weight_decay=0.0,
        lr_anneal_steps=0,
        batch_size=1,
        microbatch=-1,  # -1 disables microbatches
        ema_rate="0.9999",  # comma-separated list of EMA values
        log_interval=10,
        sample_interval=5000,  # TODO increase
        save_interval=10000,
        resume_checkpoint="",
        use_fp16=False,
        fp16_scale_growth=1e-3,
        do_inefficient_marg=False,
        n_valid_batches=1,
        n_valid_repeats=2,
        max_frames=10,
    )
    defaults.update(video_model_and_diffusion_defaults())
    parser = argparse.ArgumentParser()
    add_dict_to_argparser(parser, defaults)
    return parser


if __name__ == "__main__":
    main()
