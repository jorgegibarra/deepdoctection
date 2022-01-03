# -*- coding: utf-8 -*-
# File: hflayoutlm.py

# Copyright 2021 Dr. Janis Meyer. All rights reserved.
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

"""
HF Layoutlm models for diverse downstream tasks.
"""
from typing import List, Dict, Union
from copy import copy

from ..utils.detection_types import Requirement
from .hf.hfutils import transformers_available
from .pt.ptutils import pytorch_available
from .base import LMTokenClassifier, TokenClassResult

if pytorch_available():
    import torch

if transformers_available():
    from .pt.ptutils import get_pytorch_requirement, set_torch_auto_device
    from .hf.hfutils import get_transformers_requirement
    from .hf.layoutlm import predict_token_classes
    from transformers import LayoutLMForTokenClassification


class HFLayoutLmTokenClassifier(LMTokenClassifier):
    """
    A wrapper class for :class:`transformers.LayoutLMForTokenClassification` to use within a pipeline component.
    Check https://huggingface.co/docs/transformers/model_doc/layoutlm for documentation of the model itself.
    Note that this model is equipped with a head that is only useful when classifying tokens. For sequence
    classification and other things please use another model of the family.
    """

    def __init__(self,categories_semantics: List[str], categories_bio: List[str]):
        """
        :param categories_semantics: A dict with key (indices) and values (category names). To be consistent with
                                     detectors use only values >0. Conversion will be done internally.
        """

        self._categories = self._categories_orig_to_categories(categories_semantics,categories_bio)
        self.device = set_torch_auto_device()
        self.model = LayoutLMForTokenClassification.from_pretrained("mrm8488/layoutlm-finetuned-funsd")

    @classmethod
    def get_requirements(cls) -> List[Requirement]:
        return [get_pytorch_requirement(), get_transformers_requirement()]

    def predict(self, **encodings: Union[List[str], torch.Tensor]) -> List[TokenClassResult]:
        """
        Launch inference on LayoutLm for token classification. Pass the following arguments

        :param input_ids: Token converted to ids to be taken from LayoutLMTokenizer
        :param attention_mask: The associated attention masks from padded sequences taken from LayoutLMTokenizer
        :param token_type_ids: Torch tensor of token type ids taken from LayoutLMTokenizer
        :param boxes: Torch tensor of bounding boxes of type 'xyxy'
        :param tokens: List of original tokens taken from LayoutLMTokenizer

        :return: A list of TokenClassResults
        """

        assert "input_ids" in encodings
        assert "attention_mask" in encodings
        assert "token_type_ids" in encodings
        assert "boxes" in encodings
        assert "tokens" in encodings

        results = predict_token_classes(encodings["ids"], encodings["input_ids"],encodings["attention_mask"],
                                        encodings["token_type_ids"], encodings["boxes"],encodings["tokens"], self.model)

        return self._map_category_names(results)

    @staticmethod
    def _categories_orig_to_categories(categories_semantics: List[str], categories_bio: List[str]):
        categories_semantics = copy(categories_semantics)
        categories_bio = copy(categories_bio)
        categories_list = [x+"-"+ y for x in categories_bio for y in categories_semantics if y!="OTHER"]
        categories_list = [x for x in categories_list if not x.startswith("O")]
        categories_list.insert(9,"O")
        return {idx: cat_name for idx, cat_name in enumerate(categories_list)}

    def _map_category_names(self, token_results: List[TokenClassResult]) -> List[TokenClassResult]:
        for result in token_results:
            result.class_name = self._categories[result.class_id]
            result.semantic_name = result.class_name.split("-")[0] if "-" in  result.class_name else "OTHER"
            result.bio_tag = result.class_name.split("-")[1] if "i" in  result.class_name else "O"
        return token_results

    @property
    def categories(self):
        return self._categories
