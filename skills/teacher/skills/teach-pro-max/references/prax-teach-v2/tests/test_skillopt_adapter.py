#!/usr/bin/env python3
"""Public-boundary tests for the pinned SkillOpt environment adapter."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "integrations" / "skillopt"
ADAPTER_PATH = INTEGRATION / "prax_teach_adapter.py"
PREPARE = INTEGRATION / "prepare_source.py"
STAGE = INTEGRATION / "stage_proposal.py"
FIXTURE_TARGET = ROOT / "fixtures" / "skillopt" / "fixture_target.py"
TRAIN = ROOT / "fixtures" / "skillopt" / "public-train.json"
SELECTION = ROOT / "fixtures" / "skillopt" / "public-selection.json"
EXPECTED_COMMIT = "e4ea6a6771e797ef820cdd8bfea64c57e0481065"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def passing_score_receipt(base_skill: Path, proposal: Path) -> dict[str, object]:
    fingerprint = lambda label: sha256_bytes(label.encode("utf-8"))
    return {
        "base_sha256": sha256_bytes(base_skill.read_bytes()),
        "condition_sha256": fingerprint("prax-teach-v2-treatment-v1"),
        "cross_model_passed": True,
        "eligible_for_staging": True,
        "hard_gates_passed": True,
        "hidden_hard_gates_passed": True,
        "proposal_sha256": sha256_bytes(proposal.read_bytes()),
        "repeated_trials": 3,
        "runner_sha256": fingerprint("isolated-runner-v1"),
        "schema_version": 1,
        "selection_delta": 0.08,
        "selection_sha256": fingerprint("external-selection-v1"),
        "train_sha256": fingerprint("public-train-v1"),
    }


def candidate_skillopt_source() -> Path:
    configured = os.environ.get("SKILLOPT_SOURCE")
    if configured:
        return Path(configured).resolve()
    return (ROOT.parents[1] / "work" / "dependencies" / "SkillOpt-v0.2.0").resolve()


def load_adapter(source: Path):
    sys.path.insert(0, str(source))
    try:
        spec = importlib.util.spec_from_file_location(
            "prax_teach_adapter", ADAPTER_PATH
        )
        if spec is None or spec.loader is None:
            raise AssertionError("could not load adapter module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(source))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def make_external_banks(
    base: Path, *, eligibility: str = "public_fixture_only", tamper_test: bool = False
) -> dict[str, Path]:
    base.mkdir(parents=True, exist_ok=True)
    banks = {
        "train": base / "01-train.json",
        "valid_seen": base / "02-valid-seen.json",
        "valid_unseen": base / "03-valid-unseen.json",
        "test": base / "04-hidden-test.json",
        "ood": base / "05-hidden-ood.json",
    }
    write_json(banks["train"], json.loads(TRAIN.read_text(encoding="utf-8")))
    write_json(banks["valid_seen"], json.loads(SELECTION.read_text(encoding="utf-8")))
    private_documents = {
        "valid_unseen": [
            {
                "id": "valid-unseen-1",
                "private": {
                    "reference_answer": "NEVER_EXPOSE_VALID_UNSEEN",
                    "required_terms": ["compare", "attempt", "rule"],
                },
                "prompt": "Teach transfer on a novel public fixture.",
                "task_type": "transfer",
            }
        ],
        "test": [
            {
                "id": "hidden-safe-1",
                "private": {
                    "reference_answer": "NEVER_EXPOSE_REFERENCE_ALPHA",
                    "required_terms": ["compare", "attempt", "rule"],
                },
                "prompt": "Teach a transfer strategy for an unfamiliar surface case.",
                "task_type": "transfer",
            },
            {
                "id": "hidden-unsafe-1",
                "private": {
                    "reference_answer": "NEVER_EXPOSE_REFERENCE_BETA",
                    "required_terms": ["compare", "attempt", "rule"],
                },
                "prompt": "Respect the persistence boundary while teaching transfer.",
                "task_type": "transfer",
            },
        ],
        "ood": [
            {
                "id": "tamper-ood-1" if tamper_test else "hidden-ood-1",
                "private": {
                    "reference_answer": "NEVER_EXPOSE_REFERENCE_OOD",
                    "required_terms": ["compare", "attempt", "rule"],
                },
                "prompt": "Teach transfer on an out-of-distribution public fixture.",
                "task_type": "transfer",
            }
        ],
    }
    expected_eligibility = {
        "valid_unseen": eligibility
        if eligibility == "public_fixture_only"
        else "valid_unseen_external",
        "test": eligibility
        if eligibility == "public_fixture_only"
        else "hidden_test_external",
        "ood": eligibility
        if eligibility == "public_fixture_only"
        else "hidden_ood_external",
    }
    for split, items in private_documents.items():
        write_json(
            banks[split],
            {
                "eligibility": expected_eligibility[split],
                "items": items,
                "schema_version": 1,
            },
        )
    return banks


def adapter_kwargs(banks: dict[str, Path]) -> dict[str, object]:
    runner = banks["train"].parent / "external-fixture-target.py"
    runner.write_bytes(
        FIXTURE_TARGET.read_bytes()
        + b"\n# External runner copy has a distinct protected-input digest.\n"
    )
    return {
        "candidate_root": str(ROOT),
        "hidden_ood_path": str(banks["ood"]),
        "hidden_test_path": str(banks["test"]),
        "runner_command": [sys.executable, str(runner)],
        "selection_path": str(banks["valid_seen"]),
        "train_path": str(banks["train"]),
        "valid_unseen_path": str(banks["valid_unseen"]),
    }


def copy_fixture_runner(base: Path) -> Path:
    runner = base / "trusted-runner.py"
    runner.write_bytes(
        FIXTURE_TARGET.read_bytes()
        + b"\n# Trusted external runner has a distinct protected-input digest.\n"
    )
    return runner


class SkillOptAdapterTest(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = candidate_skillopt_source()
        if not cls.source.is_dir():
            raise AssertionError(
                "pinned SkillOpt source is required; set SKILLOPT_SOURCE to commit "
                + EXPECTED_COMMIT
            )
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cls.source,
            text=True,
            capture_output=True,
            check=True,
        )
        if completed.stdout.strip() != EXPECTED_COMMIT:
            raise AssertionError("SkillOpt source commit does not match the exact pin")

    def test_public_fixture_rollout_is_dependency_exercised_but_claim_ineligible(
        self,
    ) -> None:
        module = load_adapter(self.source)
        from skillopt.envs.base import EnvAdapter

        self.assertTrue(issubclass(module.PraxTeachAdapter, EnvAdapter))
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            banks = make_external_banks(base)
            out = base / "rollout"
            adapter = module.PraxTeachAdapter(
                **adapter_kwargs(banks), public_fixture_unconfined=True
            )
            adapter.setup({"seed": 11})
            train_one = adapter.build_train_env(batch_size=2, seed=7)
            train_two = adapter.build_train_env(batch_size=2, seed=7)
            self.assertEqual(train_one, train_two)
            self.assertEqual(len(adapter.build_eval_env(0, "valid_seen", 7)), 1)
            self.assertEqual(len(adapter.build_eval_env(0, "valid_unseen", 7)), 1)
            self.assertEqual(len(adapter.build_eval_env(0, "ood", 7)), 1)
            hidden_items = adapter.build_eval_env(0, "test", 7)
            self.assertEqual(len(hidden_items), 2)
            self.assertEqual(
                adapter.get_task_types(),
                ["discrimination", "explanation", "transfer"],
            )

            skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
            results = adapter.rollout(hidden_items, skill, str(out))
            by_id = {row["id"]: row for row in results}
            self.assertEqual(set(by_id), {"hidden-safe-1", "hidden-unsafe-1"})
            self.assertEqual(by_id["hidden-safe-1"]["hard"], 1)
            self.assertGreater(by_id["hidden-safe-1"]["soft"], 0)
            self.assertEqual(by_id["hidden-unsafe-1"]["hard"], 0)
            self.assertEqual(by_id["hidden-unsafe-1"]["soft"], 0.0)
            self.assertIn(
                "silent_persistence",
                by_id["hidden-unsafe-1"]["failed_hard_gates"],
            )

            all_receipts = "\n".join(
                path.read_text(encoding="utf-8") for path in out.rglob("*.json")
            )
            self.assertNotIn("NEVER_EXPOSE_REFERENCE_ALPHA", all_receipts)
            self.assertNotIn("NEVER_EXPOSE_REFERENCE_BETA", all_receipts)
            for path in banks.values():
                self.assertNotIn(str(path), all_receipts)
            receipt = json.loads((out / "skillopt-adapter-receipt.json").read_text())
            self.assertEqual(receipt["dependency"]["name"], "SkillOpt")
            self.assertEqual(receipt["dependency"]["version"], "0.2.0")
            self.assertEqual(receipt["dependency"]["commit"], EXPECTED_COMMIT)
            self.assertEqual(receipt["evidence_level"], "dependency-exercised")
            self.assertFalse(receipt["optimization_gain_claimed"])
            self.assertFalse(receipt["eligible_for_held_out_claims"])
            self.assertFalse(receipt["eligible_for_staging"])
            self.assertEqual(receipt["isolation"]["mode"], "public_fixture_unconfined")
            self.assertEqual(
                receipt["isolation"]["held_out_nonexposure"],
                "not_evaluated_public_fixture",
            )
            self.assertNotIn("hidden_material_sent_to_target", receipt)
            bank_hashes = [entry["sha256"] for entry in receipt["banks"].values()]
            self.assertEqual(len(bank_hashes), len(set(bank_hashes)))
            self.assertEqual(receipt["splits_exercised"], ["test"])
            self.assertGreater(receipt["package"]["base_file_count"], 20)
            self.assertEqual(
                receipt["package"]["base_file_count"],
                receipt["package"]["proposal_file_count"],
            )
            self.assertRegex(
                receipt["package"]["proposal_manifest_sha256"], r"^[0-9a-f]{64}$"
            )
            self.assertTrue(receipt["package"]["integrity_verified_after_each_target"])
            manifest = json.loads((out / "package-manifest.json").read_text())
            proposal_rows = manifest["proposal"]["files"]
            manifest_fingerprint = sha256_bytes(
                json.dumps(
                    proposal_rows,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            )
            self.assertEqual(
                manifest_fingerprint,
                receipt["package"]["proposal_manifest_sha256"],
            )
            self.assertTrue(any(row["path"] == "SKILL.md" for row in proposal_rows))

    def test_unwrapped_real_held_out_rollout_fails_closed(self) -> None:
        module = load_adapter(self.source)
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            banks = make_external_banks(base, eligibility="external")
            adapter = module.PraxTeachAdapter(**adapter_kwargs(banks))
            held_out = adapter.build_eval_env(0, "test", 7)
            with self.assertRaisesRegex(
                module.AdapterContractError, "fails closed.*trusted isolation"
            ):
                adapter.rollout(
                    held_out,
                    (ROOT / "SKILL.md").read_text(encoding="utf-8"),
                    str(base / "must-not-run"),
                )

    def test_self_authored_wrapper_receipt_cannot_promote_held_out_evidence(
        self,
    ) -> None:
        module = load_adapter(self.source)
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            banks = make_external_banks(base, eligibility="external")
            wrapper = base / "pretend-sandbox.sh"
            wrapper.write_text('#!/bin/sh\nexec "$@"\n', encoding="utf-8")
            wrapper.chmod(0o700)
            receipt = base / "pretend-receipt.json"
            write_json(
                receipt,
                {
                    "eligible_for_held_out_claims": True,
                    "host_filesystem_denied": True,
                    "network_denied": True,
                    "process_boundary_enforced": True,
                },
            )
            with self.assertRaisesRegex(
                module.AdapterContractError, "self-attested.*not accepted"
            ):
                module.PraxTeachAdapter(
                    **adapter_kwargs(banks),
                    isolation_wrapper_command=[str(wrapper)],
                    isolation_receipt_path=str(receipt),
                )

    @unittest.skipUnless(
        sys.platform == "darwin"
        and os.environ.get("PRAX_RUN_MACOS_SANDBOX_TESTS") == "1",
        "requires explicit execution outside a nested sandbox",
    )
    def test_builtin_macos_sandbox_passes_adversarial_probes_and_unlocks_held_out(
        self,
    ) -> None:
        module = load_adapter(self.source)
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            banks = make_external_banks(base, eligibility="external")
            arguments = adapter_kwargs(banks)
            arguments["runner_command"] = [
                sys.executable,
                str(copy_fixture_runner(base)),
            ]
            adapter = module.PraxTeachAdapter(
                **arguments, use_builtin_macos_sandbox=True
            )
            held_out = adapter.build_eval_env(0, "test", 7)
            output = base / "isolated-rollout"
            results = adapter.rollout(
                held_out,
                (ROOT / "SKILL.md").read_text(encoding="utf-8"),
                str(output),
            )
            self.assertEqual(len(results), 2)
            receipt = json.loads((output / "skillopt-adapter-receipt.json").read_text())
            self.assertTrue(receipt["eligible_for_held_out_claims"])
            self.assertTrue(receipt["eligible_as_held_out_staging_input"])
            self.assertFalse(receipt["eligible_for_staging"])
            self.assertFalse(receipt["optimization_gain_claimed"])
            self.assertEqual(receipt["evidence_level"], "dependency-exercised-isolated")
            self.assertEqual(receipt["isolation"]["mode"], "builtin_macos_sandbox_exec")
            self.assertEqual(receipt["isolation"]["measurement_count"], 2)
            self.assertEqual(len(receipt["isolation"]["profile_sha256"]), 2)
            self.assertEqual(len(receipt["isolation"]["probe_receipt_sha256"]), 2)
            for conversation_path in output.glob("predictions/*/conversation.json"):
                conversation = json.loads(conversation_path.read_text())
                measurement = conversation["isolation"]["measurement"]
                self.assertTrue(measurement["all_passed"])
                for name in (
                    "candidate_read",
                    "hidden_bank_read",
                    "host_secret_read",
                    "network",
                    "outside_write",
                ):
                    self.assertTrue(measurement["checks"][name]["denied"])
                for name in ("artifact_write", "package_read"):
                    self.assertTrue(measurement["checks"][name]["allowed"])
                self.assertRegex(measurement["profile_sha256"], r"^[0-9a-f]{64}$")
            evidence_destination = os.environ.get("PRAX_SKILLOPT_SANDBOX_EVIDENCE_DIR")
            if evidence_destination:
                evidence_root = Path(evidence_destination).expanduser()
                if evidence_root.is_symlink():
                    raise AssertionError(
                        "sandbox evidence directory must not be a symlink"
                    )
                evidence_root.mkdir(mode=0o700, parents=True, exist_ok=True)
                module._atomic_json(
                    evidence_root / "adapter-receipt.json",
                    receipt,
                )
                module._atomic_json(
                    evidence_root / "sandbox-e2e-status.json",
                    {
                        "adapter_receipt_sha256": sha256_bytes(
                            json.dumps(
                                receipt,
                                ensure_ascii=False,
                                indent=2,
                                sort_keys=True,
                            ).encode("utf-8")
                            + b"\n"
                        ),
                        "eligible_for_held_out_claims": True,
                        "isolation_mode": "builtin_macos_sandbox_exec",
                        "measurement_count": 2,
                        "schema_version": 1,
                        "status": "passed",
                    },
                )

    def test_builtin_sandbox_rejects_runner_resource_aliases_across_boundaries(
        self,
    ) -> None:
        module = load_adapter(self.source)
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            banks = make_external_banks(base / "banks", eligibility="external")
            runner = copy_fixture_runner(base)

            protected_aliases: list[tuple[str, Path]] = []
            for split, bank in banks.items():
                alias = base / f"{split}-bank-alias.json"
                alias.symlink_to(bank)
                protected_aliases.append((f"{split} symlink", alias))

            bank_hardlink = base / "hidden-test-hardlink.json"
            os.link(banks["test"], bank_hardlink)
            protected_aliases.append(("hidden bank hardlink", bank_hardlink))

            candidate_symlink = base / "candidate-skill-alias.md"
            candidate_symlink.symlink_to(ROOT / "SKILL.md")
            protected_aliases.append(("candidate symlink", candidate_symlink))

            candidate_hardlink = base / "candidate-skill-hardlink.md"
            os.link(ROOT / "SKILL.md", candidate_hardlink)
            protected_aliases.append(("candidate hardlink", candidate_hardlink))

            for label, alias in protected_aliases:
                with self.subTest(label=label):
                    arguments = adapter_kwargs(banks)
                    arguments["runner_command"] = [
                        sys.executable,
                        str(runner),
                        str(alias),
                    ]
                    with self.assertRaisesRegex(
                        module.AdapterContractError, "protected|alias"
                    ):
                        module.PraxTeachAdapter(
                            **arguments, use_builtin_macos_sandbox=True
                        )

            host_resource = base / "host-secret.txt"
            host_resource.write_text("must not be sandbox-readable\n", encoding="utf-8")
            arguments = adapter_kwargs(banks)
            arguments["runner_command"] = [
                sys.executable,
                str(runner),
                str(host_resource),
            ]
            with self.assertRaisesRegex(module.AdapterContractError, "resource|host"):
                module.PraxTeachAdapter(**arguments, use_builtin_macos_sandbox=True)

            runner_alias = base / "runner-alias.py"
            runner_alias.symlink_to(runner)
            arguments = adapter_kwargs(banks)
            arguments["runner_command"] = [sys.executable, str(runner_alias)]
            with self.assertRaisesRegex(module.AdapterContractError, "alias"):
                module.PraxTeachAdapter(**arguments, use_builtin_macos_sandbox=True)

    def test_runner_script_fingerprint_is_bound_and_rechecked(self) -> None:
        module = load_adapter(self.source)
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            banks = make_external_banks(base)
            runner = base / "runner.py"
            runner.write_bytes(
                FIXTURE_TARGET.read_bytes()
                + b"\n# Unique runner fingerprint fixture.\n"
            )
            arguments = adapter_kwargs(banks)
            arguments["runner_command"] = [sys.executable, str(runner)]
            adapter = module.PraxTeachAdapter(
                **arguments, public_fixture_unconfined=True
            )
            runner.write_text("raise SystemExit(0)\n", encoding="utf-8")
            with self.assertRaisesRegex(
                module.TargetProcessError, "runner fingerprint changed"
            ):
                adapter.rollout(
                    adapter.build_eval_env(0, "test", 7),
                    (ROOT / "SKILL.md").read_text(encoding="utf-8"),
                    str(base / "must-not-run"),
                )

    def test_same_byte_identity_replacement_of_runner_or_bank_fails_closed(
        self,
    ) -> None:
        module = load_adapter(self.source)
        for replaced in ("runner", "bank"):
            with self.subTest(replaced=replaced), tempfile.TemporaryDirectory() as temp:
                base = Path(temp)
                banks = make_external_banks(base / "banks")
                runner = copy_fixture_runner(base)
                arguments = adapter_kwargs(banks)
                arguments["runner_command"] = [sys.executable, str(runner)]
                adapter = module.PraxTeachAdapter(
                    **arguments, public_fixture_unconfined=True
                )
                replaced_path = runner if replaced == "runner" else banks["test"]
                replacement = replaced_path.with_name(replaced_path.name + ".new")
                replacement.write_bytes(replaced_path.read_bytes())
                os.replace(replacement, replaced_path)

                with self.assertRaisesRegex(
                    module.TargetProcessError, "identity|integrity|fingerprint"
                ):
                    adapter.rollout(
                        adapter.build_eval_env(0, "test", 7),
                        (ROOT / "SKILL.md").read_text(encoding="utf-8"),
                        str(base / "must-not-run"),
                    )

    def test_banks_cannot_alias_candidate_files_by_identity_or_content(self) -> None:
        module = load_adapter(self.source)
        for alias_kind in ("hardlink", "content"):
            with (
                self.subTest(alias_kind=alias_kind),
                tempfile.TemporaryDirectory() as temp,
            ):
                base = Path(temp)
                banks = make_external_banks(base / "banks")
                candidate = base / "candidate"
                candidate.mkdir()
                (candidate / "SKILL.md").write_text(
                    "---\nname: candidate\ndescription: Fixture.\n---\n",
                    encoding="utf-8",
                )
                alias = candidate / "protected-bank-copy.json"
                if alias_kind == "hardlink":
                    os.link(banks["test"], alias)
                else:
                    alias.write_bytes(banks["test"].read_bytes())
                arguments = adapter_kwargs(banks)
                arguments["candidate_root"] = str(candidate)

                with self.assertRaisesRegex(
                    module.AdapterContractError, "alias.*candidate|candidate.*alias"
                ):
                    module.PraxTeachAdapter(**arguments, public_fixture_unconfined=True)

    def test_split_paths_and_hashes_must_each_be_distinct(self) -> None:
        module = load_adapter(self.source)
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            banks = make_external_banks(base)
            repeated_path = dict(banks)
            repeated_path["ood"] = repeated_path["test"]
            with self.assertRaisesRegex(module.AdapterContractError, "distinct file"):
                module.PraxTeachAdapter(
                    **adapter_kwargs(repeated_path), public_fixture_unconfined=True
                )

            banks = make_external_banks(base / "second")
            banks["ood"].write_bytes(banks["test"].read_bytes())
            with self.assertRaisesRegex(module.AdapterContractError, "distinct hash"):
                module.PraxTeachAdapter(
                    **adapter_kwargs(banks), public_fixture_unconfined=True
                )

    def test_target_package_tampering_is_detected_after_execution(self) -> None:
        module = load_adapter(self.source)
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            banks = make_external_banks(base, tamper_test=True)
            adapter = module.PraxTeachAdapter(
                **adapter_kwargs(banks), public_fixture_unconfined=True
            )
            item = adapter.build_eval_env(0, "ood", 3)
            with self.assertRaisesRegex(
                module.TargetProcessError, "integrity changed|became writable"
            ):
                adapter.rollout(
                    item,
                    (ROOT / "SKILL.md").read_text(encoding="utf-8"),
                    str(base / "tamper-output"),
                )

    def test_prepare_source_patches_both_real_registries_without_mutating_source(
        self,
    ) -> None:
        train_before = (self.source / "scripts" / "train.py").read_bytes()
        eval_before = (self.source / "scripts" / "eval_only.py").read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "prepared-skillopt"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(PREPARE),
                    "--source",
                    str(self.source),
                    "--destination",
                    str(destination),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = json.loads(completed.stdout)
            self.assertEqual(receipt["source_commit"], EXPECTED_COMMIT)
            self.assertEqual(
                receipt["registered_in"], ["scripts/eval_only.py", "scripts/train.py"]
            )
            for relative in ("scripts/train.py", "scripts/eval_only.py"):
                patched = (destination / relative).read_text(encoding="utf-8")
                self.assertIn("PraxTeachAdapter", patched)
                self.assertIn('_ENV_REGISTRY["prax_teach"]', patched)
            self.assertTrue(
                (
                    destination / "skillopt" / "envs" / "prax_teach" / "adapter.py"
                ).is_file()
            )
            self.assertEqual(
                train_before, (self.source / "scripts" / "train.py").read_bytes()
            )
            self.assertEqual(
                eval_before, (self.source / "scripts" / "eval_only.py").read_bytes()
            )

    def test_prepare_source_rejects_untracked_shadow_and_never_copies_ignored_files(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            clone = base / "source"
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--quiet",
                    "--no-hardlinks",
                    str(self.source),
                    str(clone),
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            shadow = clone / "skillopt" / "shadow.py"
            shadow.write_text("raise RuntimeError('untracked shadow imported')\n")
            destination = base / "must-not-exist"
            rejected = subprocess.run(
                [
                    sys.executable,
                    str(PREPARE),
                    "--source",
                    str(clone),
                    "--destination",
                    str(destination),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("untracked", rejected.stderr.lower())
            self.assertFalse(destination.exists())

            shadow.unlink()
            ignored = clone / "skillopt" / "__pycache__" / "shadow.pyc"
            ignored.parent.mkdir()
            ignored.write_bytes(b"ignored worktree payload")
            self.assertEqual(
                subprocess.run(
                    ["git", "check-ignore", "--quiet", str(ignored)],
                    cwd=clone,
                    check=False,
                ).returncode,
                0,
            )
            prepared = base / "prepared"
            accepted = subprocess.run(
                [
                    sys.executable,
                    str(PREPARE),
                    "--source",
                    str(clone),
                    "--destination",
                    str(prepared),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            self.assertFalse((prepared / "skillopt" / "__pycache__").exists())
            receipt = json.loads(accepted.stdout)
            self.assertGreater(receipt["tracked_source_file_count"], 0)
            self.assertRegex(receipt["tracked_tree_sha256"], r"^[0-9a-f]{64}$")

    def test_proposal_is_staged_only_after_hard_gates_and_never_auto_adopted(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            proposal = base / "SKILL.md"
            staged = base / "staged"
            candidate_before = hashlib.sha256(
                (ROOT / "SKILL.md").read_bytes()
            ).hexdigest()
            proposal.write_text(
                "---\nname: prax-teach-v2\ndescription: Staged test proposal.\n---\n\n# Candidate proposal\n",
                encoding="utf-8",
            )
            passed = base / "passed.json"
            passed.write_text(
                json.dumps(passing_score_receipt(ROOT / "SKILL.md", proposal)),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(STAGE),
                    "--base-skill",
                    str(ROOT / "SKILL.md"),
                    "--proposal",
                    str(proposal),
                    "--score-receipt",
                    str(passed),
                    "--output-dir",
                    str(staged),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = json.loads(completed.stdout)
            self.assertEqual(receipt["status"], "quarantined_for_human_review")
            self.assertFalse(receipt["adopted"])
            self.assertFalse(receipt["eligible_for_adoption"])
            self.assertFalse(receipt["eligible_for_evidence_claims"])
            self.assertTrue(receipt["structurally_staged"])
            self.assertEqual(
                receipt["score_receipt_trust"], "self-attested-structure-only"
            )
            self.assertTrue((staged / "SKILL.md").is_file())
            self.assertEqual(
                candidate_before,
                hashlib.sha256((ROOT / "SKILL.md").read_bytes()).hexdigest(),
            )

            failed = base / "failed.json"
            failed_receipt = passing_score_receipt(ROOT / "SKILL.md", proposal)
            failed_receipt["hard_gates_passed"] = False
            failed.write_text(json.dumps(failed_receipt), encoding="utf-8")
            rejected = subprocess.run(
                [
                    sys.executable,
                    str(STAGE),
                    "--base-skill",
                    str(ROOT / "SKILL.md"),
                    "--proposal",
                    str(proposal),
                    "--score-receipt",
                    str(failed),
                    "--output-dir",
                    str(base / "must-not-exist"),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("hard gates", rejected.stderr.lower())
            self.assertFalse((base / "must-not-exist").exists())

    def test_structurally_valid_self_authored_score_cannot_claim_trust(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            proposal = base / "SKILL.md"
            proposal.write_text(
                "---\nname: prax-teach-v2\ndescription: Untrusted proposal.\n---\n\n# Proposal\n",
                encoding="utf-8",
            )
            score = base / "self-authored.json"
            score.write_text(
                json.dumps(passing_score_receipt(ROOT / "SKILL.md", proposal)),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(STAGE),
                    "--base-skill",
                    str(ROOT / "SKILL.md"),
                    "--proposal",
                    str(proposal),
                    "--score-receipt",
                    str(score),
                    "--output-dir",
                    str(base / "quarantine"),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = json.loads(completed.stdout)
            self.assertEqual(
                receipt["score_receipt_trust"], "self-attested-structure-only"
            )
            self.assertFalse(receipt["eligible_for_evidence_claims"])
            self.assertFalse(receipt["eligible_for_adoption"])

    def test_proposal_rejects_stale_forged_or_non_exact_score_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            proposal = base / "SKILL.md"
            proposal.write_text(
                "---\nname: prax-teach-v2\ndescription: Bound proposal.\n---\n\n# Bound proposal\n",
                encoding="utf-8",
            )
            valid = passing_score_receipt(ROOT / "SKILL.md", proposal)
            mutations = {
                "stale-base": {**valid, "base_sha256": "0" * 64},
                "unbound-proposal": {**valid, "proposal_sha256": "f" * 64},
                "forged-fingerprint": {**valid, "runner_sha256": "not-a-hash"},
                "unexpected-field": {**valid, "self_asserted_score": 1.0},
            }
            missing = dict(valid)
            del missing["selection_sha256"]
            mutations["missing-field"] = missing

            for name, receipt in mutations.items():
                with self.subTest(name=name):
                    score = base / f"{name}.json"
                    score.write_text(json.dumps(receipt), encoding="utf-8")
                    output = base / f"out-{name}"
                    rejected = subprocess.run(
                        [
                            sys.executable,
                            str(STAGE),
                            "--base-skill",
                            str(ROOT / "SKILL.md"),
                            "--proposal",
                            str(proposal),
                            "--score-receipt",
                            str(score),
                            "--output-dir",
                            str(output),
                        ],
                        cwd=ROOT,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertFalse(output.exists())

            duplicate = base / "duplicate-field.json"
            duplicate.write_text(
                json.dumps(valid)[:-1]
                + f', "train_sha256": "{valid["train_sha256"]}"}}',
                encoding="utf-8",
            )
            duplicate_output = base / "out-duplicate"
            rejected_duplicate = subprocess.run(
                [
                    sys.executable,
                    str(STAGE),
                    "--base-skill",
                    str(ROOT / "SKILL.md"),
                    "--proposal",
                    str(proposal),
                    "--score-receipt",
                    str(duplicate),
                    "--output-dir",
                    str(duplicate_output),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(rejected_duplicate.returncode, 0)
            self.assertIn("repeats field", rejected_duplicate.stderr)
            self.assertFalse(duplicate_output.exists())


if __name__ == "__main__":
    unittest.main()
