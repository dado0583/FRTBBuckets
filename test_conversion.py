from Converter import Delta
import os
import json

def test_single_curve():
    path = os.getcwd() + "/test_data/single_curve/SingleCurve.json"

    expected_total=300
    expected_91 = 151.64835164835165

    check_curve_deltas(path, expected_total, expected_91)

def test_two_curves():
    path = os.getcwd() + "/test_data/single_curve/TwoCurves.json"

    expected_total=11700
    expected_91 = 303.2967032967033

    check_curve_deltas(path, expected_total, expected_91, expected_20Y=497.80821917808214, expected_30Y=10502.191780821919)
    #20Y and 30Y values won't be completely round because of difference in day count convention used in calculation
    #which is flat 365 days per year and by swaps 

def test_many_curves():
    path = os.getcwd() + "/test_data/many_curves/Input.json"

    expected_total=-771310.45973682159
    expected_91 = 68504.685988740865

    check_curve_deltas(path, expected_total, expected_91)

def test_vega_curves():
    path = os.getcwd() + "/test_data/single_curve/single_vega.json"

    expected_total=3000.0000000000005
    expected_91 = 0

    check_vegas(path, expected_total, expected_91)

def check_vegas(path, expected_total, expected_91, expected_20Y=0, expected_30Y=0):
    with open(path) as json_file:
        json_data = json.load(json_file)

    results = Delta().convert(json_data)

    for result in results['vegas']:
        r = results['vegas'][result]
        assert expected_total == r.values.sum()

def check_curve_deltas(path, expected_total, expected_91, expected_20Y=0, expected_30Y=0):
    with open(path) as json_file:
        json_data = json.load(json_file)

    results = Delta().convert(json_data)

    actual_total = 0
    actual_91 = 0
    actual_20Y = 0
    actual_30Y = 0

    for result in results['deltas']:
        r = results['deltas'][result]
        #Summing all the values across the curve
        actual_total += r.values.sum()

        #Note that result[91] returns a series. This contains all the input
        #points that has some value that should be bucketed to the 91 day tenor
        #Therefore we need to sum.
        actual_91 += r[91].values.sum()
        actual_20Y += r[7300].values.sum()
        actual_30Y += r[10950].values.sum()

    #Summing all the values across the curve
    assert actual_total == expected_total

    #Note that result[91] returns a series. This contains all the input
    #points that has some value that should be bucketed to the 91 day tenor
    #Therefore we need to sum.
    assert actual_91 == expected_91

    if expected_20Y != 0:
        assert actual_20Y == expected_20Y
    if expected_30Y != 0:
        assert actual_30Y == expected_30Y

    return results

if __name__ == "__main__":
    #test_single_curve()
    #test_two_curves()
    test_many_curves()
    test_vega_curves()
