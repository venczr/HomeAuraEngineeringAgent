using System;
using System.Collections.Generic;

using HomeAura.AutoCAD.Agent;

namespace HomeAura.AutoCAD.Agent.Tests
{
    internal static class Program
    {
        private static int passed;

        private static int Main()
        {
            try
            {
                Run(
                    "simple rectangle",
                    TestSimpleRectangle
                );
                Run(
                    "reverse vertex direction",
                    TestReverseDirection
                );
                Run(
                    "duplicate vertices",
                    TestDuplicateVertices
                );
                Run(
                    "self intersection",
                    TestSelfIntersection
                );
                Run(
                    "arc segment",
                    TestArcSegment
                );
                Run(
                    "nested contours",
                    TestNestedContours
                );
                Run(
                    "millimeters and meters",
                    TestDrawingUnits
                );
                Run(
                    "MagiCAD area difference",
                    TestAreaDifference
                );

                Console.WriteLine(
                    "PASS: " + passed +
                    " room geometry tests"
                );

                return 0;
            }
            catch (System.Exception exception)
            {
                Console.Error.WriteLine(
                    "FAIL: " + exception.Message
                );

                return 1;
            }
        }

        private static void TestSimpleRectangle()
        {
            List<RoomBoundaryVertex> vertices =
                Rectangle(0, 0, 4, 3);

            int removed;

            List<RoomBoundaryVertex> normalized =
                RoomGeometryMath.NormalizeVertices(
                    vertices,
                    1e-9,
                    true,
                    out removed
                );

            AssertEqual(0, removed, "removed");
            AssertEqual(
                4,
                normalized.Count,
                "vertex count"
            );
            AssertNear(
                12,
                RoomGeometryMath.CalculateSignedArea(
                    normalized
                ),
                1e-9,
                "area"
            );
            AssertEqual(
                "CCW",
                RoomGeometryMath.GetDirection(
                    normalized
                ),
                "direction"
            );
            AssertFalse(
                RoomGeometryMath
                    .HasSelfIntersections(
                        normalized,
                        0.01,
                        1e-9
                    ),
                "rectangle self-intersects"
            );

            RoomBoundary boundary =
                ValidBoundary(normalized, 12);

            AssertTrue(
                RoomGeometryMath.ContainsPoint(
                    boundary,
                    2,
                    1
                ),
                "point must be inside"
            );
            AssertFalse(
                RoomGeometryMath.ContainsPoint(
                    boundary,
                    5,
                    1
                ),
                "point must be outside"
            );
        }

        private static void TestReverseDirection()
        {
            List<RoomBoundaryVertex> clockwise =
                new List<RoomBoundaryVertex>
                {
                    Vertex(0, 0),
                    Vertex(0, 3),
                    Vertex(4, 3),
                    Vertex(4, 0)
                };

            AssertEqual(
                "CW",
                RoomGeometryMath.GetDirection(
                    clockwise
                ),
                "original direction"
            );

            List<RoomBoundaryVertex> normalized =
                RoomGeometryMath
                    .NormalizeCounterClockwise(
                        clockwise
                    );

            AssertEqual(
                "CCW",
                RoomGeometryMath.GetDirection(
                    normalized
                ),
                "normalized direction"
            );
            AssertNear(
                12,
                RoomGeometryMath.CalculateSignedArea(
                    normalized
                ),
                1e-9,
                "normalized area"
            );
        }

        private static void TestDuplicateVertices()
        {
            List<RoomBoundaryVertex> source =
                new List<RoomBoundaryVertex>
                {
                    Vertex(0, 0),
                    Vertex(4, 0),
                    Vertex(4, 0),
                    Vertex(4, 3),
                    Vertex(0, 3),
                    Vertex(0, 0)
                };

            int removed;

            List<RoomBoundaryVertex> normalized =
                RoomGeometryMath.NormalizeVertices(
                    source,
                    1e-8,
                    true,
                    out removed
                );

            AssertEqual(
                2,
                removed,
                "duplicate count"
            );
            AssertEqual(
                4,
                normalized.Count,
                "logical closure vertex count"
            );
        }

        private static void TestSelfIntersection()
        {
            List<RoomBoundaryVertex> bowTie =
                new List<RoomBoundaryVertex>
                {
                    Vertex(0, 0),
                    Vertex(4, 4),
                    Vertex(0, 4),
                    Vertex(4, 0)
                };

            AssertTrue(
                RoomGeometryMath
                    .HasSelfIntersections(
                        bowTie,
                        0.01,
                        1e-9
                    ),
                "bow-tie must self-intersect"
            );
        }

        private static void TestArcSegment()
        {
            List<RoomBoundaryVertex> vertices =
                new List<RoomBoundaryVertex>
                {
                    Vertex(0, 0, 1),
                    Vertex(2, 0),
                    Vertex(2, 2),
                    Vertex(0, 2)
                };

            double expectedArea =
                4 + Math.PI / 2;

            AssertNear(
                expectedArea,
                RoomGeometryMath.CalculateSignedArea(
                    vertices
                ),
                1e-9,
                "arc signed area"
            );

            List<RoomBoundaryVertex> flattened =
                RoomGeometryMath.Flatten(
                    vertices,
                    0.01
                );

            AssertTrue(
                flattened.Count > 5,
                "arc must be discretized"
            );

            RoomBoundary boundary =
                ValidBoundary(
                    vertices,
                    expectedArea
                );

            boundary.Diagnostics
                .ArcChordToleranceDrawingUnits = 0.01;

            AssertTrue(
                RoomGeometryMath.ContainsPoint(
                    boundary,
                    1,
                    1
                ),
                "point inside arc contour"
            );
        }

        private static void TestNestedContours()
        {
            RoomBoundary outer =
                ValidBoundary(
                    Rectangle(0, 0, 10, 10),
                    100
                );

            outer.SourceHandle = "OUTER";

            RoomBoundary inner =
                ValidBoundary(
                    Rectangle(4, 4, 6, 6),
                    4
                );

            inner.SourceHandle = "INNER";

            int containingCount;

            RoomBoundary selected =
                RoomGeometryMath
                    .SelectSmallestContaining(
                        new List<RoomBoundary>
                        {
                            outer,
                            inner
                        },
                        5,
                        5,
                        out containingCount
                    );

            AssertEqual(
                2,
                containingCount,
                "containing count"
            );
            AssertEqual(
                "INNER",
                selected.SourceHandle,
                "selected handle"
            );
        }

        private static void TestDrawingUnits()
        {
            double millimeters;
            double meters;

            AssertTrue(
                RoomGeometryMath
                    .TryGetMetersPerDrawingUnit(
                        "Millimeters",
                        out millimeters
                    ),
                "millimeters recognized"
            );

            AssertTrue(
                RoomGeometryMath
                    .TryGetMetersPerDrawingUnit(
                        "Meters",
                        out meters
                    ),
                "meters recognized"
            );

            AssertNear(
                0.001,
                millimeters,
                1e-12,
                "millimeter factor"
            );
            AssertNear(
                1,
                meters,
                1e-12,
                "meter factor"
            );
        }

        private static void TestAreaDifference()
        {
            RoomBoundary boundary =
                ValidBoundary(
                    Rectangle(0, 0, 5, 4),
                    20
                );

            AssertNear(
                3,
                RoomGeometryMath
                    .CalculateAreaDifferenceM2(
                        17,
                        boundary
                    ).Value,
                1e-9,
                "area difference"
            );

            AssertNear(
                17.6470588235,
                RoomGeometryMath
                    .CalculateAreaDifferencePercent(
                        17,
                        boundary
                    ).Value,
                1e-9,
                "area difference percent"
            );
        }

        private static RoomBoundary ValidBoundary(
            List<RoomBoundaryVertex> vertices,
            double area)
        {
            RoomBoundary boundary =
                new RoomBoundary
                {
                    SourceHandle = "TEST",
                    SourceObjectType = "LWPOLYLINE",
                    SourceLayer = "0",
                    Vertices = vertices,
                    IsClosed = true,
                    ContourAreaM2 = area,
                    Direction =
                        RoomGeometryMath.GetDirection(
                            vertices
                        ),
                    DrawingUnits = "Meters",
                    MetersPerDrawingUnit = 1,
                    GeometrySource = "Test"
                };

            boundary.Diagnostics.IsSupported = true;
            boundary.Diagnostics.IsValid = true;
            boundary.Diagnostics
                .VertexToleranceDrawingUnits = 1e-9;
            boundary.Diagnostics
                .ArcChordToleranceDrawingUnits = 0.001;

            return boundary;
        }

        private static List<RoomBoundaryVertex>
            Rectangle(
                double minimumX,
                double minimumY,
                double maximumX,
                double maximumY)
        {
            return new List<RoomBoundaryVertex>
            {
                Vertex(minimumX, minimumY),
                Vertex(maximumX, minimumY),
                Vertex(maximumX, maximumY),
                Vertex(minimumX, maximumY)
            };
        }

        private static RoomBoundaryVertex Vertex(
            double x,
            double y,
            double bulge = 0)
        {
            return new RoomBoundaryVertex
            {
                X = x,
                Y = y,
                Z = 0,
                Bulge = bulge,
                SegmentType =
                    Math.Abs(bulge) <= 1e-12
                        ? "Line"
                        : "Arc"
            };
        }

        private static void Run(
            string name,
            Action test)
        {
            test();
            passed++;
            Console.WriteLine("ok - " + name);
        }

        private static void AssertTrue(
            bool value,
            string message)
        {
            if (!value)
            {
                throw new InvalidOperationException(
                    message
                );
            }
        }

        private static void AssertFalse(
            bool value,
            string message)
        {
            AssertTrue(!value, message);
        }

        private static void AssertNear(
            double expected,
            double actual,
            double tolerance,
            string message)
        {
            if (Math.Abs(expected - actual) >
                tolerance)
            {
                throw new InvalidOperationException(
                    message +
                    ": expected " +
                    expected +
                    ", actual " +
                    actual
                );
            }
        }

        private static void AssertEqual<T>(
            T expected,
            T actual,
            string message)
        {
            if (!EqualityComparer<T>
                    .Default.Equals(
                        expected,
                        actual
                    ))
            {
                throw new InvalidOperationException(
                    message +
                    ": expected " +
                    expected +
                    ", actual " +
                    actual
                );
            }
        }
    }
}
