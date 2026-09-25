internal static class TwoFloorGeometryNegativeValidation
{
    public static void Run()
    {
        Require(Relation(((0,0),(4,4)), ((0,4),(4,0))) == "PROPER_CROSSING", "proper crossing fixture");
        Require(Relation(((0,0),(4,0)), ((2,0),(2,3))) == "T_TOUCH", "T-touch fixture");
        Require(Relation(((0,0),(4,0)), ((4,0),(4,3))) == "POINT_TOUCH", "point touch fixture");
        Require(Relation(((0,0),(5,0)), ((2,0),(7,0))) == "COLLINEAR_OVERLAP", "partial overlap fixture");
        Require(Relation(((0,0),(5,0)), ((5,0),(0,0))) == "COLLINEAR_OVERLAP", "reverse overlap fixture");
        Require(!ValidRoute([(0,0),(1,1)]), "diagonal route accepted");
        Require(!ValidRoute([(0,0),(0,0),(0,2)]), "zero segment accepted");
        Require(!ValidRoute([(0,0),(4,0),(4,4),(2,4),(2,0)]), "self T-touch accepted");
        Require(!ValidRoute([(0,0),(4,0),(2,0),(2,3)]), "self overlap accepted");
        Require(ValidRoute([(0,0),(4,0),(4,4)]), "valid route rejected");
        Require(HitsBox(((0,0),(4,0)), (2,-1,3,1)), "box interior crossing missed");
        Require(HitsBox(((0,0),(2,0)), (2,0,3,1)), "box boundary touch missed");
        Require(!HitsBox(((0,0),(1,0)), (2,0,3,1)), "disjoint box false positive");
        Require(Length([(0,0),(4,0),(4,5)]) == 900, "length fixture");
    }

    private static bool ValidRoute((int X,int Y)[] points)
    {
        if (points.Length < 2) return false;
        for (var i=0;i<points.Length-1;i++)
            if (points[i] == points[i+1] || (points[i].X != points[i+1].X && points[i].Y != points[i+1].Y)) return false;
        for (var i=0;i<points.Length-1;i++)
        for (var j=i+2;j<points.Length-1;j++)
            if (Relation((points[i],points[i+1]),(points[j],points[j+1])) != "DISJOINT") return false;
        return true;
    }

    private static int Length((int X,int Y)[] points) => points.Zip(points.Skip(1)).Sum(pair =>
        (Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);

    private static bool HitsBox(((int X,int Y) A,(int X,int Y) B) segment,(int X0,int Y0,int X1,int Y1) box)
    {
        static bool Inside((int X,int Y) p,(int X0,int Y0,int X1,int Y1) b) => p.X>=b.X0&&p.X<=b.X1&&p.Y>=b.Y0&&p.Y<=b.Y1;
        if (Inside(segment.A,box)||Inside(segment.B,box)) return true;
        var edges = new[] {((box.X0,box.Y0),(box.X1,box.Y0)),((box.X1,box.Y0),(box.X1,box.Y1)),((box.X1,box.Y1),(box.X0,box.Y1)),((box.X0,box.Y1),(box.X0,box.Y0))};
        return edges.Any(edge => Relation(segment,edge)!="DISJOINT");
    }

    private static string Relation(((int X,int Y) A,(int X,int Y) B) first,((int X,int Y) A,(int X,int Y) B) second)
    {
        static long Cross((int X,int Y) p,(int X,int Y) q,(int X,int Y) r)=>(long)(q.X-p.X)*(r.Y-p.Y)-(long)(q.Y-p.Y)*(r.X-p.X);
        var a=first.A;var b=first.B;var c=second.A;var d=second.B;
        var v=new[]{Cross(a,b,c),Cross(a,b,d),Cross(c,d,a),Cross(c,d,b)};
        if(v.All(value=>value==0))
        {
            var ox=Math.Min(Math.Max(a.X,b.X),Math.Max(c.X,d.X))-Math.Max(Math.Min(a.X,b.X),Math.Min(c.X,d.X));
            var oy=Math.Min(Math.Max(a.Y,b.Y),Math.Max(c.Y,d.Y))-Math.Max(Math.Min(a.Y,b.Y),Math.Min(c.Y,d.Y));
            if(Math.Max(ox,oy)>0)return "COLLINEAR_OVERLAP";
            if(ox==0&&oy==0)return "POINT_TOUCH";
            return "DISJOINT";
        }
        var hit=(v[0]==0||v[1]==0||(v[0]<0)!=(v[1]<0))&&(v[2]==0||v[3]==0||(v[2]<0)!=(v[3]<0));
        if(!hit)return "DISJOINT";
        if(a==c||a==d||b==c||b==d)return "POINT_TOUCH";
        return v.Contains(0)?"T_TOUCH":"PROPER_CROSSING";
    }

    private static void Require(bool condition,string message)
    {
        if(!condition)throw new InvalidDataException(message);
    }
}
