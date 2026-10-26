from collections import defaultdict
import unittest

import pygame

from main import Entity, HISTORY_RATE, TimeWarpGame, WARP_SECONDS


class TimeWarpGameTests(unittest.TestCase):
    keys = defaultdict(bool)

    def test_starts_with_nine_lives_and_no_stars(self):
        game = TimeWarpGame(seed=1)
        self.assertEqual(game.player.lives, 9)
        self.assertEqual(game.player.stars, 0)

    def test_collecting_a_star_adds_a_life_and_score(self):
        game = TimeWarpGame(seed=1)
        game.entities.append(
            Entity("star", game.player.x, game.player.y, 13, 0)
        )
        game.update(self.keys, 1 / 60)
        self.assertEqual(game.player.lives, 10)
        self.assertEqual(game.player.stars, 1)
        self.assertEqual(game.score, 100)

    def test_warp_restores_world_but_keeps_run_stats(self):
        game = TimeWarpGame(seed=1)
        keys = self.keys
        for _ in range(HISTORY_RATE * WARP_SECONDS * 2):
            game.update(keys, 1 / 60)

        self.assertEqual(len(game.history), HISTORY_RATE * WARP_SECONDS + 1)
        game.player.stars = 5
        game.score = 321
        game.player.lives = 12
        portal_x, portal_y = game._portal_position()
        game.player.x, game.player.y = portal_x, portal_y
        game.update(keys, 1 / 60)

        self.assertTrue(game.replay)
        self.assertEqual(game.player.stars, 0)
        self.assertEqual(game.player.lives, 12)
        self.assertEqual(game.score, 321)
        self.assertLess(game.elapsed, 1 / 30)


if __name__ == "__main__":
    unittest.main()
