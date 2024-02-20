# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import sys
import typing

from pytriton.client import ModelClient, DecoupledModelClient
import numpy as np


def get_args(argv):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=f"Exports nemo models stored in nemo checkpoints to TensorRT-LLM",
    )
    parser.add_argument(
        "-u",
        "--url",
        default="0.0.0.0",
        type=str,
        help="url for the triton server"
    )
    parser.add_argument(
        "-mn",
        "--model_name",
        required=True,
        type=str,
        help="Name of the triton model"
    )
    parser.add_argument(
        "-p",
        "--prompt",
        required=True,
        type=str,
        help="Prompt"
    )
    parser.add_argument(
        "-swl",
        "--stop_words_list",
        type=str,
        help="Stop words list"
    )
    parser.add_argument(
        "-bwl",
        "--bad_words_list",
        type=str,
        help="Bad words list"
    )
    parser.add_argument(
        "-nrns",
        "--no_repeat_ngram_size",
        type=int,
        help="No repeat ngram size"
    )
    parser.add_argument(
        "-mot",
        "--max_output_token",
        default=128,
        type=int,
        help="Max output token length"
    )
    parser.add_argument(
        "-tk",
        "--top_k",
        default=1,
        type=int,
        help="top_k"
    )
    parser.add_argument(
        "-tp",
        "--top_p",
        default=0.0,
        type=float,
        help="top_p"
    )
    parser.add_argument(
        "-t",
        "--temperature",
        default=1.0,
        type=float,
        help="temperature"
    )
    parser.add_argument(
        "-ti",
        "--task_id",
        type=str,
        help="Task id for the prompt embedding tables"
    )
    parser.add_argument(
        "-es",
        '--enable_streaming',
        default=False,
        action='store_true',
        help="Enables streaming sentences."
    )
    parser.add_argument(
        "-it",
        "--init_timeout",
        default=60.0,
        type=float,
        help="init timeout for the triton server"
    )

    args = parser.parse_args(argv)
    return args


def str_list2numpy(str_list: typing.List[str]) -> np.ndarray:
    str_ndarray = np.array(str_list)[..., np.newaxis]
    return np.char.encode(str_ndarray, "utf-8")


def query_llm(
        url,
        model_name,
        prompts,
        stop_words_list=None,
        bad_words_list=None,
        no_repeat_ngram_size=None,
        max_output_token=128,
        top_k=1,
        top_p=0.0,
        temperature=1.0,
        random_seed=None,
        task_id=None,
        init_timeout=60.0
):
    prompts = str_list2numpy(prompts)
    inputs = {"prompts": prompts}

    if max_output_token is not None:
        inputs["max_output_token"] = np.full(prompts.shape, max_output_token, dtype=np.int_)

    if top_k is not None:
        inputs["top_k"] = np.full(prompts.shape, top_k, dtype=np.int_)

    if top_p is not None:
        inputs["top_p"] = np.full(prompts.shape, top_p, dtype=np.single)

    if temperature is not None:
        inputs["temperature"] = np.full(prompts.shape, temperature, dtype=np.single)

    if random_seed is not None:
        inputs["random_seed"] = np.full(prompts.shape, random_seed, dtype=np.single)

    if stop_words_list is not None:
        stop_words_list = np.char.encode(stop_words_list, "utf-8")
        inputs["stop_words_list"] = np.full((prompts.shape[0], len(stop_words_list)), stop_words_list)

    if bad_words_list is not None:
        bad_words_list = np.char.encode(bad_words_list, "utf-8")
        inputs["bad_words_list"] = np.full((prompts.shape[0], len(bad_words_list)), bad_words_list)

    if no_repeat_ngram_size is not None:
        inputs["no_repeat_ngram_size"] = np.full(prompts.shape, no_repeat_ngram_size, dtype=np.single)

    if task_id is not None:
        task_id = np.char.encode(task_id, "utf-8")
        inputs["task_id"] = np.full((prompts.shape[0], len([task_id])), task_id)

    with ModelClient(url, model_name, init_timeout_s=init_timeout) as client:
        result_dict = client.infer_batch(**inputs)
        output_type = client.model_config.outputs[0].dtype

    if output_type == np.bytes_:
        sentences = np.char.decode(result_dict["outputs"].astype("bytes"), "utf-8")
        return sentences
    else:
        return result_dict["outputs"]


def query_llm_streaming(
        url,
        model_name,
        prompts,
        stop_words_list=None,
        bad_words_list=None,
        no_repeat_ngram_size=None,
        max_output_token=512,
        top_k=1,
        top_p=0.0,
        temperature=1.0,
        random_seed=None,
        task_id=None,
        init_timeout=60.0,
):
    prompts = str_list2numpy(prompts)
    inputs = {"prompts": prompts}

    if max_output_token is not None:
        inputs["max_output_token"] = np.full(prompts.shape, max_output_token, dtype=np.int_)

    if top_k is not None:
        inputs["top_k"] = np.full(prompts.shape, top_k, dtype=np.int_)

    if top_p is not None:
        inputs["top_p"] = np.full(prompts.shape, top_p, dtype=np.single)

    if temperature is not None:
        inputs["temperature"] = np.full(prompts.shape, temperature, dtype=np.single)

    if random_seed is not None:
        inputs["random_seed"] = np.full(prompts.shape, random_seed, dtype=np.int_)

    if stop_words_list is not None:
        stop_words_list = np.char.encode(stop_words_list, "utf-8")
        inputs["stop_words_list"] = np.full((prompts.shape[0], len(stop_words_list)), stop_words_list)

    if bad_words_list is not None:
        bad_words_list = np.char.encode(bad_words_list, "utf-8")
        inputs["bad_words_list"] = np.full((prompts.shape[0], len(bad_words_list)), bad_words_list)

    if no_repeat_ngram_size is not None:
        inputs["no_repeat_ngram_size"] = np.full(prompts.shape, no_repeat_ngram_size, dtype=np.single)

    if task_id is not None:
        task_id = np.char.encode(task_id, "utf-8")
        inputs["task_id"] = np.full((prompts.shape[0], len([task_id])), task_id)

    with DecoupledModelClient(url, model_name, init_timeout_s=init_timeout) as client:
        for partial_result_dict in client.infer_batch(**inputs):
            output_type = client.model_config.outputs[0].dtype
            if output_type == np.bytes_:
                sentences = np.char.decode(partial_result_dict["outputs"].astype("bytes"), "utf-8")
                yield sentences
            else:
                yield partial_result_dict["outputs"]


def query(argv):
    args = get_args(argv)

    if args.enable_streaming:
        output = query_llm_streaming(
            url=args.url,
            model_name=args.model_name,
            prompts=[args.prompt],
            stop_words_list=None if args.stop_words_list is None else [args.stop_words_list],
            bad_words_list=None if args.bad_words_list is None else [args.bad_words_list],
            no_repeat_ngram_size=args.no_repeat_ngram_size,
            max_output_token=args.max_output_token,
            top_k=args.top_k,
            top_p=args.top_p,
            temperature=args.temperature,
            task_id=args.task_id,
            init_timeout=args.init_timeout,
        )

        print("output: ")
        for o in output:
            print(o)
    else:
        output = query_llm(
            url=args.url,
            model_name=args.model_name,
            prompts=[args.prompt],
            stop_words_list=None if args.stop_words_list is None else [args.stop_words_list],
            bad_words_list=None if args.bad_words_list is None else [args.bad_words_list],
            no_repeat_ngram_size=args.no_repeat_ngram_size,
            max_output_token=args.max_output_token,
            top_k=args.top_k,
            top_p=args.top_p,
            temperature=args.temperature,
            task_id=args.task_id,
            init_timeout=args.init_timeout,
        )
        print("output: ", output)


if __name__ == '__main__':
    query(sys.argv[1:])
