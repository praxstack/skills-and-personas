"""Ordinary argument controls for the pinned sandbox browser launcher."""
import unittest

from chromium_wrapper import BASE_ARGS, browser_arguments


class BrowserArgumentsTests(unittest.TestCase):
    def features(self, arguments):
        actual = browser_arguments(arguments)
        flags = [arg for arg in actual if arg.startswith('--enable-features=')]
        self.assertEqual(len(flags), 1)
        self.assertEqual(actual[:len(BASE_ARGS)], BASE_ARGS)
        return actual, flags[0].partition('=')[2].split(',')

    def test_no_existing_switch(self):
        actual, features = self.features(['--mute-audio', '--remote-debugging-pipe'])
        self.assertEqual(features, ['BrowserThreadPoolAdjustment:min/2'])
        self.assertIn('--mute-audio', actual)
        self.assertIn('--remote-debugging-pipe', actual)

    def test_existing_unrelated_features_and_arguments_survive(self):
        arguments = ['--enable-features=CDPScreenshotNewSurface,Foo:k/v',
                     '--disable-features=Other', '--user-data-dir=/tmp/profile',
                     '--enable-features', 'Bar<Study.Group']
        actual, features = self.features(arguments)
        self.assertEqual(features, ['CDPScreenshotNewSurface', 'Foo:k/v',
                                    'Bar<Study.Group', 'BrowserThreadPoolAdjustment:min/2'])
        self.assertIn('--disable-features=Other', actual)
        self.assertIn('--user-data-dir=/tmp/profile', actual)

    def test_conflicting_owned_feature_replaced_once(self):
        _, features = self.features(['--enable-features=BrowserThreadPoolAdjustment:min/16,Foo',
                                    '--enable-features=BrowserThreadPoolAdjustment<Old.Group:min/32'])
        self.assertEqual(features, ['Foo', 'BrowserThreadPoolAdjustment:min/2'])

    def test_incomplete_separate_value_is_rejected(self):
        for arguments in [['--enable-features'], ['--enable-features', '--mute-audio']]:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                browser_arguments(arguments)


if __name__ == '__main__':
    unittest.main()
