# v3.0.1 package verification

Source revision: `33cfd556ed0387c0b4991fcb6d4bb6f2ae912fad`.

The source and standalone ZIPs were built twice from committed Git objects.
All three archive hashes reproduced byte for byte. Archive CRC, traversal and
link checks passed. A source-ZIP install into an isolated agent folder matched
every teacher file. The standalone wrapper ZIP passed its 759-file engine
integrity check with no sibling teacher present.

| Asset | Bytes | Files | SHA-256 |
|---|---:|---:|---|
| prax-teach-v3.0.1-source.zip | 7,946,554 | 1,549 | fc974c6b549ccb8a6ca8a1940db18ea2005d07fe2939f9fb94163c7295ca4bba |
| teacher.zip | 4,384,944 | 742 | 53e12ee416a14a1a5758095eaad6c7deda9358a9ef6c13189ae96b7c13c0956a |
| teach-pro-max.zip | 3,535,630 | 804 | d63eb41bea4acee57f4ab26cc7383c1487b09b54d28c3f46da0ac09f3df32d98 |

The tracked compatibility ZIP is refreshed from these same bytes. The release
manifest and checksum file stay outside the ZIPs they attest to. Runtime weights
and the Docker image are not bundled. The old lessons remain downloadable from
v3.0.0; this patch does not claim new lesson content or a new quality score.

These final hashes supersede the unshipped c53fb6f package candidate after the Linux process-limit fix. The initial package receipt remains in Git history. The exact standalone skills CLI 1.7.2 install also passed with only teach-pro-max selected.
