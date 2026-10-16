# Accessible interaction fallback

Below is a self-contained practice page. JavaScript adds feedback; without JavaScript, the complete worksheet, hints, and native answer key remain available.

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Hash-table load-factor practice</title>

  <style>
    :root {
      color-scheme: light dark;
      --page: #f7f7fb;
      --panel: #ffffff;
      --text: #20202a;
      --muted: #5b5b69;
      --border: #777784;
      --accent: #3157c8;
      --correct: #176b42;
      --incorrect: #a12828;
    }

    @media (prefers-color-scheme: dark) {
      :root {
        --page: #17171c;
        --panel: #24242b;
        --text: #f4f4f7;
        --muted: #c1c1cb;
        --border: #9696a3;
        --accent: #9cb7ff;
        --correct: #79d7a5;
        --incorrect: #ff9a9a;
      }
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background: var(--page);
      color: var(--text);
      font: 1rem/1.55 system-ui, sans-serif;
    }

    header,
    main,
    footer {
      width: min(44rem, calc(100% - 2rem));
      margin-inline: auto;
    }

    header {
      padding-block: 2rem 1rem;
    }

    main {
      padding-bottom: 3rem;
    }

    h1,
    h2 {
      line-height: 1.2;
    }

    .skip-link {
      position: absolute;
      left: 1rem;
      top: -5rem;
      padding: 0.75rem;
      background: var(--panel);
      color: var(--text);
      z-index: 10;
    }

    .skip-link:focus {
      top: 1rem;
    }

    :focus-visible {
      outline: 3px solid var(--accent);
      outline-offset: 3px;
    }

    .rule,
    .notice,
    details,
    .case,
    #summary {
      padding: 1rem;
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      background: var(--panel);
    }

    .case {
      margin-block: 1rem;
    }

    .case > legend {
      padding-inline: 0.35rem;
      font-weight: 700;
    }

    .case[data-result="correct"] {
      border-inline-start: 0.4rem solid var(--correct);
    }

    .case[data-result="incorrect"] {
      border-inline-start: 0.4rem solid var(--incorrect);
    }

    label {
      display: block;
      margin-block: 0.75rem 0.25rem;
      font-weight: 650;
    }

    input[type="number"] {
      width: min(100%, 12rem);
      padding: 0.65rem;
      border: 1px solid var(--border);
      border-radius: 0.35rem;
      background: var(--panel);
      color: var(--text);
      font: inherit;
    }

    .decision {
      margin-block-start: 1rem;
      border: 0;
      padding: 0;
    }

    .decision label {
      display: inline-flex;
      gap: 0.45rem;
      align-items: center;
      margin-inline-end: 1.5rem;
      font-weight: 500;
    }

    .feedback {
      min-height: 1.6em;
      margin-block-end: 0;
      font-weight: 650;
    }

    .feedback.correct {
      color: var(--correct);
    }

    .feedback.incorrect {
      color: var(--incorrect);
    }

    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-block: 1.5rem;
    }

    button {
      min-height: 2.75rem;
      padding: 0.65rem 1rem;
      border: 2px solid var(--accent);
      border-radius: 0.4rem;
      background: var(--accent);
      color: #fff;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }

    button.secondary {
      background: var(--panel);
      color: var(--text);
    }

    summary {
      cursor: pointer;
      font-weight: 700;
    }

    details + details {
      margin-block-start: 0.75rem;
    }

    #summary:empty {
      display: none;
    }

    footer {
      padding-block: 1rem 2rem;
      color: var(--muted);
    }

    /* The interface has no essential animation. */
    @media (prefers-reduced-motion: reduce) {
      *,
      *::before,
      *::after {
        scroll-behavior: auto !important;
        animation-duration: 0.001ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.001ms !important;
      }
    }

    @media print {
      .skip-link,
      .actions,
      .feedback,
      #summary,
      noscript {
        display: none !important;
      }

      body {
        background: #fff;
        color: #000;
      }

      .case,
      details {
        break-inside: avoid;
        background: #fff;
      }

      details:not([open]) > :not(summary) {
        display: block !important;
      }

      #answer-key {
        break-before: page;
      }
    }
  </style>

  <noscript>
    <style>
      .actions {
        display: none;
      }
    </style>
  </noscript>
</head>

<body>
  <a class="skip-link" href="#practice">Skip to practice</a>

  <header>
    <h1>Hash-table load-factor practice</h1>
    <p>Calculate load factors and decide whether a table should rehash.</p>
  </header>

  <main id="main">
    <section aria-labelledby="rule-heading">
      <h2 id="rule-heading">Decision rule</h2>

      <p class="rule" id="rule">
        <strong>Load factor:</strong>
        α = number of entries ÷ number of buckets.
        Rehash only when α is <strong>strictly greater than</strong> the stated
        threshold. Enter load factors rounded to three decimal places.
      </p>

      <details>
        <summary>Worked example</summary>
        <p>
          With 3 entries and 8 buckets, α = 3 ÷ 8 = 0.375.
          At a threshold of 0.75, the table does not rehash because
          0.375 is not greater than 0.75.
        </p>
      </details>

      <details>
        <summary>Hint ladder</summary>
        <ol>
          <li>Identify the entries and buckets.</li>
          <li>Divide entries by buckets.</li>
          <li>Compare the unrounded result with the threshold using <code>&gt;</code>.</li>
        </ol>
      </details>
    </section>

    <section id="practice" aria-labelledby="practice-heading">
      <h2 id="practice-heading">Practice</h2>

      <noscript>
        <p class="notice">
          Automatic feedback requires JavaScript. Complete every case, then
          open the static answer key below to check your work.
        </p>
      </noscript>

      <form id="practice-form" novalidate>
        <fieldset class="case" id="case-a">
          <legend>Case A</legend>
          <p id="prompt-a">
            The table has <strong>6 entries</strong>, <strong>8 buckets</strong>,
            and a rehash threshold of <strong>0.75</strong>.
          </p>

          <label for="alpha-a">Load factor, rounded to three decimals</label>
          <input
            id="alpha-a"
            type="number"
            min="0"
            step="0.001"
            inputmode="decimal"
            aria-describedby="prompt-a rule feedback-a"
          >

          <fieldset class="decision" aria-describedby="prompt-a rule feedback-a">
            <legend>Should the table rehash?</legend>
            <label><input type="radio" name="rehash-a" value="yes"> Yes</label>
            <label><input type="radio" name="rehash-a" value="no"> No</label>
          </fieldset>

          <p class="feedback" id="feedback-a" aria-live="polite"></p>
        </fieldset>

        <fieldset class="case" id="case-b">
          <legend>Case B</legend>
          <p id="prompt-b">
            The table has <strong>7 entries</strong>, <strong>8 buckets</strong>,
            and a rehash threshold of <strong>0.75</strong>.
          </p>

          <label for="alpha-b">Load factor, rounded to three decimals</label>
          <input
            id="alpha-b"
            type="number"
            min="0"
            step="0.001"
            inputmode="decimal"
            aria-describedby="prompt-b rule feedback-b"
          >

          <fieldset class="decision" aria-describedby="prompt-b rule feedback-b">
            <legend>Should the table rehash?</legend>
            <label><input type="radio" name="rehash-b" value="yes"> Yes</label>
            <label><input type="radio" name="rehash-b" value="no"> No</label>
          </fieldset>

          <p class="feedback" id="feedback-b" aria-live="polite"></p>
        </fieldset>

        <fieldset class="case" id="case-c">
          <legend>Case C</legend>
          <p id="prompt-c">
            The table has <strong>9 entries</strong>, <strong>12 buckets</strong>,
            and a rehash threshold of <strong>0.70</strong>.
          </p>

          <label for="alpha-c">Load factor, rounded to three decimals</label>
          <input
            id="alpha-c"
            type="number"
            min="0"
            step="0.001"
            inputmode="decimal"
            aria-describedby="prompt-c rule feedback-c"
          >

          <fieldset class="decision" aria-describedby="prompt-c rule feedback-c">
            <legend>Should the table rehash?</legend>
            <label><input type="radio" name="rehash-c" value="yes"> Yes</label>
            <label><input type="radio" name="rehash-c" value="no"> No</label>
          </fieldset>

          <p class="feedback" id="feedback-c" aria-live="polite"></p>
        </fieldset>

        <fieldset class="case" id="case-d">
          <legend>Transfer case D</legend>
          <p id="prompt-d">
            A table must hold <strong>10 entries</strong>. Its threshold is
            <strong>0.65</strong>. What is the smallest whole number of buckets
            that keeps its load factor at or below the threshold?
          </p>

          <label for="buckets-d">Minimum number of buckets</label>
          <input
            id="buckets-d"
            type="number"
            min="1"
            step="1"
            inputmode="numeric"
            aria-describedby="prompt-d feedback-d"
          >

          <p class="feedback" id="feedback-d" aria-live="polite"></p>
        </fieldset>

        <div class="actions">
          <button id="check" type="button">Check answers</button>
          <button class="secondary" type="reset">Reset</button>
        </div>
      </form>

      <p id="summary" role="status" tabindex="-1"></p>

      <details id="answer-key">
        <summary>Static answer key — reveal after attempting every case</summary>
        <ol>
          <li><strong>A:</strong> 6 ÷ 8 = 0.750; no rehash because equality does not exceed the threshold.</li>
          <li><strong>B:</strong> 7 ÷ 8 = 0.875; rehash because 0.875 is greater than 0.75.</li>
          <li><strong>C:</strong> 9 ÷ 12 = 0.750; rehash because 0.750 is greater than 0.70.</li>
          <li><strong>D:</strong> 16 buckets. Ten divided by 16 is 0.625, while ten divided by 15 is approximately 0.667.</li>
        </ol>
      </details>
    </section>
  </main>

  <footer>
    <p>No responses are stored or transmitted.</p>
  </footer>

  <script>
    (() => {
      const form = document.querySelector("#practice-form");
      const summary = document.querySelector("#summary");

      const cases = [
        { id: "a", entries: 6, buckets: 8, threshold: 0.75 },
        { id: "b", entries: 7, buckets: 8, threshold: 0.75 },
        { id: "c", entries: 9, buckets: 12, threshold: 0.70 }
      ];

      function gradeLoadFactor(item) {
        const container = document.querySelector(`#case-${item.id}`);
        const alphaInput = document.querySelector(`#alpha-${item.id}`);
        const decisionInputs = [
          ...document.querySelectorAll(`[name="rehash-${item.id}"]`)
        ];
        const selected = decisionInputs.find(input => input.checked);
        const feedback = document.querySelector(`#feedback-${item.id}`);

        const exact = item.entries / item.buckets;
        const rounded = Number(exact.toFixed(3));
        const expectedDecision = exact > item.threshold ? "yes" : "no";
        const submittedAlpha = Number.parseFloat(alphaInput.value);

        const alphaCorrect =
          Number.isFinite(submittedAlpha) &&
          Math.abs(submittedAlpha - rounded) < 0.0006;

        const decisionCorrect =
          Boolean(selected) && selected.value === expectedDecision;

        alphaInput.setAttribute("aria-invalid", String(!alphaCorrect));
        decisionInputs.forEach(input => {
          input.setAttribute("aria-invalid", String(!decisionCorrect));
        });

        if (!Number.isFinite(submittedAlpha) || !selected) {
          feedback.textContent =
            "Incomplete: enter a load factor and choose a rehash decision.";
          feedback.className = "feedback incorrect";
          container.dataset.result = "incorrect";
          return false;
        }

        if (alphaCorrect && decisionCorrect) {
          const comparison =
            expectedDecision === "yes"
              ? "exceeds the threshold"
              : "does not exceed the threshold";

          feedback.textContent =
            `Correct: α = ${rounded.toFixed(3)}, which ${comparison}.`;
          feedback.className = "feedback correct";
          container.dataset.result = "correct";
          return true;
        }

        if (alphaCorrect) {
          feedback.textContent =
            `Your load factor, ${rounded.toFixed(3)}, is correct. ` +
            `Revise the decision by comparing it with ${item.threshold.toFixed(2)} ` +
            `using “strictly greater than.”`;
        } else if (decisionCorrect) {
          feedback.textContent =
            "Your rehash decision is correct. Recalculate entries ÷ buckets " +
            "and round the result to three decimals.";
        } else {
          feedback.textContent =
            "Recalculate entries ÷ buckets first. Then compare the unrounded " +
            "result with the threshold.";
        }

        feedback.className = "feedback incorrect";
        container.dataset.result = "incorrect";
        return false;
      }

      function gradeTransfer() {
        const container = document.querySelector("#case-d");
        const input = document.querySelector("#buckets-d");
        const feedback = document.querySelector("#feedback-d");
        const submitted = Number.parseInt(input.value, 10);
        const correct = submitted === 16;

        input.setAttribute("aria-invalid", String(!correct));

        if (correct) {
          feedback.textContent =
            "Correct: 10 ÷ 16 = 0.625. One fewer bucket gives 10 ÷ 15 ≈ 0.667, which is too high.";
          feedback.className = "feedback correct";
          container.dataset.result = "correct";
          return true;
        }

        if (!Number.isInteger(submitted)) {
          feedback.textContent = "Enter a whole number of buckets.";
        } else {
          feedback.textContent =
            "Not yet. Test your number and one fewer bucket. The smallest valid answer must satisfy 10 ÷ buckets ≤ 0.65.";
        }

        feedback.className = "feedback incorrect";
        container.dataset.result = "incorrect";
        return false;
      }

      document.querySelector("#check").addEventListener("click", () => {
        const results = cases.map(gradeLoadFactor);
        results.push(gradeTransfer());

        const correctCount = results.filter(Boolean).length;
        const firstIncorrect = results.findIndex(result => !result);

        summary.textContent =
          correctCount === results.length
            ? "All four checks are correct on this attempt. Try explaining the boundary rule in your own words."
            : `${correctCount} of ${results.length} checks are correct. Revise Case ${"ABCD"[firstIncorrect]} first.`;

        summary.focus();
      });

      form.addEventListener("reset", () => {
        document.querySelectorAll(".feedback").forEach(element => {
          element.textContent = "";
          element.className = "feedback";
        });

        document.querySelectorAll(".case").forEach(element => {
          delete element.dataset.result;
        });

        document.querySelectorAll("[aria-invalid]").forEach(element => {
          element.removeAttribute("aria-invalid");
        });

        summary.textContent = "";
        document.querySelector("#alpha-a").focus();
      });
    })();
  </script>
</body>
</html>
```
