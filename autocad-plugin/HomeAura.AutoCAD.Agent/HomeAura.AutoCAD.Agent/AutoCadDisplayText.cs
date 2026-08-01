using System;
using System.Globalization;
using System.Text;

namespace HomeAura.AutoCAD.Agent
{
    internal static class AutoCadDisplayText
    {
        internal const int IdentifierLimit = 64;
        internal const int NameLimit = 160;
        internal const int MessageLimit = 240;
        internal const int PathLimit = 320;
        internal const string MissingValue = "(нет данных)";

        internal static string Format(
            string value,
            int maximumLength)
        {
            if (maximumLength < 8 || maximumLength > 512)
            {
                throw new ArgumentOutOfRangeException(
                    "maximumLength",
                    maximumLength,
                    "Display length must be between 8 and 512."
                );
            }

            if (string.IsNullOrEmpty(value))
            {
                return MissingValue;
            }

            StringBuilder output = new StringBuilder(
                Math.Min(value.Length, maximumLength + 1)
            );
            bool previousWasSpace = false;
            int inputLimit = Math.Min(
                value.Length,
                maximumLength * 4
            );

            for (int index = 0;
                 index < inputLimit;
                 index++)
            {
                char current = value[index];
                bool validSurrogatePair =
                    char.IsHighSurrogate(current) &&
                    index + 1 < value.Length &&
                    char.IsLowSurrogate(value[index + 1]);
                UnicodeCategory category;

                if (validSurrogatePair)
                {
                    category = CharUnicodeInfo.GetUnicodeCategory(
                        value,
                        index
                    );
                }
                else if (char.IsSurrogate(current))
                {
                    category = UnicodeCategory.Surrogate;
                }
                else
                {
                    category = char.GetUnicodeCategory(current);
                }

                if (IsUnsafeCategory(category) ||
                    char.IsWhiteSpace(current))
                {
                    AppendCollapsedSpace(
                        output,
                        ref previousWasSpace
                    );

                    if (validSurrogatePair)
                    {
                        index++;
                    }

                    if (output.Length > maximumLength)
                    {
                        break;
                    }

                    continue;
                }

                output.Append(current);
                if (validSurrogatePair)
                {
                    output.Append(value[index + 1]);
                    index++;
                }
                previousWasSpace = false;

                if (output.Length > maximumLength)
                {
                    break;
                }
            }

            while (output.Length > 0 &&
                   output[output.Length - 1] == ' ')
            {
                output.Length--;
            }

            if (output.Length == 0)
            {
                return MissingValue;
            }

            if (output.Length <= maximumLength)
            {
                return output.ToString();
            }

            int prefixLength = maximumLength - 3;
            if (prefixLength > 0 &&
                prefixLength < output.Length &&
                char.IsHighSurrogate(
                    output[prefixLength - 1]) &&
                char.IsLowSurrogate(output[prefixLength]))
            {
                prefixLength--;
            }

            return output.ToString(0, prefixLength) + "...";
        }

        private static bool IsUnsafeCategory(
            UnicodeCategory category)
        {
            return
                category == UnicodeCategory.Control ||
                category == UnicodeCategory.Format ||
                category == UnicodeCategory.LineSeparator ||
                category == UnicodeCategory.ParagraphSeparator ||
                category == UnicodeCategory.Surrogate;
        }

        private static void AppendCollapsedSpace(
            StringBuilder output,
            ref bool previousWasSpace)
        {
            if (output.Length > 0 && !previousWasSpace)
            {
                output.Append(' ');
                previousWasSpace = true;
            }
        }
    }
}
