# v3.0.1 package verification

Source revision: `c53fb6ff01210e2fd9cf19c91636b36bca979764`.

The source and standalone ZIPs were built twice from committed Git objects.
All three archive hashes reproduced byte for byte. Archive CRC, traversal and
link checks passed. A source-ZIP install into an isolated agent folder matched
every teacher file. The standalone wrapper ZIP passed its 759-file engine
integrity check with no sibling teacher present.

| Asset | Bytes | Files | SHA-256 |
|---|---:|---:|---|
| prax-teach-v3.0.1-source.zip | 7,946,469 | 1,549 | c51dcad334f15930976a286f6daa223f5438a62d2967d1de056a8e4042601cdb |
| teacher.zip | 4,384,859 | 742 | 8b2df7009f477813332b427559313cd8c2eb301eba70891d8603d075645d7d9b |
| teach-pro-max.zip | 3,535,630 | 804 | d63eb41bea4acee57f4ab26cc7383c1487b09b54d28c3f46da0ac09f3df32d98 |

The tracked compatibility ZIP is refreshed from these same bytes. The release
manifest and checksum file stay outside the ZIPs they attest to. Runtime weights
and the Docker image are not bundled. The old lessons remain downloadable from
v3.0.0; this patch does not claim new lesson content or a new quality score.
