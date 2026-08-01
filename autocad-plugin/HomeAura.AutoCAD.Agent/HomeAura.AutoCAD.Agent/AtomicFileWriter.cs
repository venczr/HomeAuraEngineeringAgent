using System;
using System.IO;

namespace HomeAura.AutoCAD.Agent
{
    internal static class AtomicFileWriter
    {
        public static void PublishHistoryThenCurrent(
            string historyPath,
            string currentPath,
            Action<string> historyPublisher,
            Action<string> currentPublisher)
        {
            if (string.IsNullOrWhiteSpace(historyPath))
            {
                throw new ArgumentException(
                    "History path is required.",
                    "historyPath"
                );
            }

            if (string.IsNullOrWhiteSpace(currentPath))
            {
                throw new ArgumentException(
                    "Current path is required.",
                    "currentPath"
                );
            }

            if (historyPublisher == null)
            {
                throw new ArgumentNullException(
                    "historyPublisher"
                );
            }

            if (currentPublisher == null)
            {
                throw new ArgumentNullException(
                    "currentPublisher"
                );
            }

            historyPublisher(historyPath);
            currentPublisher(currentPath);
        }

        public static void Write(
            string path,
            Action<Stream> writer)
        {
            WriteCore(path, writer, true);
        }

        public static void WriteNew(
            string path,
            Action<Stream> writer)
        {
            WriteCore(path, writer, false);
        }

        private static void WriteCore(
            string path,
            Action<Stream> writer,
            bool replaceExisting)
        {
            if (string.IsNullOrWhiteSpace(path))
            {
                throw new ArgumentException(
                    "Destination path is required.",
                    "path"
                );
            }

            if (writer == null)
            {
                throw new ArgumentNullException("writer");
            }

            string destinationPath = Path.GetFullPath(path);
            string directory =
                Path.GetDirectoryName(destinationPath);

            if (string.IsNullOrWhiteSpace(directory))
            {
                throw new InvalidOperationException(
                    "Destination directory is unavailable."
                );
            }

            string temporaryPath = Path.Combine(
                directory,
                "." + Path.GetFileName(destinationPath) +
                "." + Guid.NewGuid().ToString("N") +
                ".tmp"
            );

            try
            {
                using (FileStream stream =
                       new FileStream(
                           temporaryPath,
                           FileMode.CreateNew,
                           FileAccess.Write,
                           FileShare.None))
                {
                    writer(stream);
                    stream.Flush(true);
                }

                if (replaceExisting &&
                    File.Exists(destinationPath))
                {
                    File.Replace(
                        temporaryPath,
                        destinationPath,
                        null
                    );
                }
                else
                {
                    File.Move(
                        temporaryPath,
                        destinationPath
                    );
                }
            }
            finally
            {
                if (File.Exists(temporaryPath))
                {
                    File.Delete(temporaryPath);
                }
            }
        }
    }
}
