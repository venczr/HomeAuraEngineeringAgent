using System;
using System.Collections.Generic;
using System.Globalization;

namespace HomeAura.AutoCAD.Agent
{
    internal sealed class RemoteHandleCandidate
    {
        internal RemoteHandleCandidate(
            int diagnosticIndex,
            long handleValue)
        {
            DiagnosticIndex = diagnosticIndex;
            HandleValue = handleValue;
        }

        public int DiagnosticIndex { get; private set; }

        public long HandleValue { get; private set; }
    }

    internal sealed class RemoteHandleSelectionPlan
    {
        private readonly IList<RemoteHandleCandidate> candidates;

        private RemoteHandleSelectionPlan(
            int totalCount,
            int malformedCount,
            int duplicateCount,
            List<RemoteHandleCandidate> candidates)
        {
            TotalCount = totalCount;
            MalformedCount = malformedCount;
            DuplicateCount = duplicateCount;
            this.candidates = candidates.AsReadOnly();
        }

        public int TotalCount { get; private set; }

        public int MalformedCount { get; private set; }

        public int DuplicateCount { get; private set; }

        public IList<RemoteHandleCandidate> Candidates
        {
            get { return candidates; }
        }

        public static RemoteHandleSelectionPlan Create(
            IList<string> handles)
        {
            if (handles == null)
            {
                throw new ArgumentNullException("handles");
            }

            int malformedCount = 0;
            int duplicateCount = 0;
            HashSet<long> seen = new HashSet<long>();
            List<RemoteHandleCandidate> candidates =
                new List<RemoteHandleCandidate>();

            for (int index = 0;
                 index < handles.Count;
                 index++)
            {
                long handleValue;

                if (string.IsNullOrWhiteSpace(handles[index]) ||
                    !long.TryParse(
                        handles[index],
                        NumberStyles.HexNumber,
                        CultureInfo.InvariantCulture,
                        out handleValue) ||
                    handleValue <= 0)
                {
                    malformedCount++;
                    continue;
                }

                if (!seen.Add(handleValue))
                {
                    duplicateCount++;
                    continue;
                }

                candidates.Add(
                    new RemoteHandleCandidate(
                        index,
                        handleValue
                    )
                );
            }

            return new RemoteHandleSelectionPlan(
                handles.Count,
                malformedCount,
                duplicateCount,
                candidates
            );
        }

        public string FormatSkippedSummary(
            int notFoundCount)
        {
            if (notFoundCount < 0 ||
                notFoundCount > candidates.Count)
            {
                throw new ArgumentOutOfRangeException(
                    "notFoundCount"
                );
            }

            if (MalformedCount == 0 &&
                DuplicateCount == 0 &&
                notFoundCount == 0)
            {
                return string.Empty;
            }

            return
                "\nПропущено Handle: некорректных — " +
                MalformedCount.ToString(
                    CultureInfo.InvariantCulture) +
                "; повторных — " +
                DuplicateCount.ToString(
                    CultureInfo.InvariantCulture) +
                "; не найдено в текущем DWG — " +
                notFoundCount.ToString(
                    CultureInfo.InvariantCulture) +
                ".";
        }
    }
}
