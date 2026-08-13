from __future__ import annotations

import unittest
from types import SimpleNamespace

from uv_studio.editor.dubbing_review_commands import (
    DubbingReviewCommandError,
    DubbingReviewCommandService,
)


class DubbingReviewAcceptanceOverlapTests(unittest.TestCase):
    @staticmethod
    def _review(*, review_id="review_new", source_id="src_1", start=2_000_000, end=4_000_000):
        return SimpleNamespace(
            review_id=review_id,
            source_id=source_id,
            target_start_us=start,
            target_end_us=end,
        )

    @staticmethod
    def _accepted(*, review_id="review_old", accepted_id="accepted_old", source_id="src_1", start=0, end=2_000_000):
        return SimpleNamespace(
            review_id=review_id,
            accepted_id=accepted_id,
            source_id=source_id,
            target_start_us=start,
            target_end_us=end,
        )

    def test_adjacent_ranges_are_allowed(self) -> None:
        review = self._review(start=2_000_000, end=4_000_000)
        state = SimpleNamespace(edits=(self._accepted(start=0, end=2_000_000),))
        DubbingReviewCommandService._reject_overlapping_acceptance(review, state)

    def test_overlap_on_same_source_is_rejected_before_acceptance(self) -> None:
        review = self._review(start=1_500_000, end=4_000_000)
        state = SimpleNamespace(edits=(self._accepted(start=0, end=2_000_000),))
        with self.assertRaisesRegex(DubbingReviewCommandError, "must not overlap"):
            DubbingReviewCommandService._reject_overlapping_acceptance(review, state)

    def test_same_range_on_different_source_is_independent(self) -> None:
        review = self._review(source_id="src_2", start=1_000_000, end=3_000_000)
        state = SimpleNamespace(
            edits=(self._accepted(source_id="src_1", start=1_000_000, end=3_000_000),)
        )
        DubbingReviewCommandService._reject_overlapping_acceptance(review, state)

    def test_same_review_cannot_be_accepted_twice_even_when_range_is_adjacent(self) -> None:
        review = self._review(review_id="review_same", start=2_000_000, end=4_000_000)
        state = SimpleNamespace(
            edits=(
                self._accepted(
                    review_id="review_same",
                    accepted_id="accepted_existing",
                    start=0,
                    end=2_000_000,
                ),
            )
        )
        with self.assertRaisesRegex(DubbingReviewCommandError, "already accepted"):
            DubbingReviewCommandService._reject_overlapping_acceptance(review, state)


if __name__ == "__main__":
    unittest.main()
