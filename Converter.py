import json
import os
from pandas.io.json import json_normalize
import pandas as pd
import numpy as np

class Delta(object):
    def __init__(self):
        pass

    def convert(self, json_data):
        output = {}
        
        delta_output = self.get_delta_output(json_data)
        output['deltas'] = delta_output

        vega_output = self.get_vega_output(json_data)
        output['vegas'] = vega_output

        return output

    def get_vega_output(self, json_data):
        df = self.__get_df(json_data, type="BUCKETED_VEGA")

        if df is None:
            return None

        df[['vega']] = df[['vega']].apply(pd.to_numeric)
        df = df.fillna(0)

        vertexes=[180, 360, 3*360, 5*360, 10*360]

        vega_output = {}

        #We're going to process each curve separately. We'll need to maintain this level
        #of segregation for the capital calcs!
        for curve in df['discriminator'].unique():
            tmp = df[df['discriminator'] == curve]
            input_vegas = pd.pivot_table(tmp, values='vega', index=['daysToExpiry'], columns=['daysSwapTerm'], aggfunc=np.sum)
            input_vegas = input_vegas.fillna(0)
            factors = self.__get_factors(input_vegas, ref_vertexes=vertexes)

            output_vegas_for_curve = np.zeros((5,5))

            #Index=OptionMaturity, Columns=Residual Maturity
            #We're going to flatten option maturity first
            # num_output_vertexes = len(vertexes)
            #tmp_df = np.zeros((num_output_vertexes,input_vegas.shape[1]))
            #vega_surface = pd.DataFrame(data=tmp_df, index=vertexes, columns=input_vegas.columns.values)

            #E.g. data, will print out as I'm going through.
            """
            Option Mat/SwapTerm     0.0     2.0     5.0     7.0     10.0
            1                               
            2
            90
            270
            540                             100        
            730
            """

            for j in range(0, input_vegas.shape[1]):
                #We're processing a column at a time...
                """
                Option Mat/SwapTerm     2.0 
                1                               
                2
                90
                270
                540                     100        
                730
                """
                tmp = input_vegas.iloc[:, j]
                tmp = tmp.fillna(0)

                tmp_df = pd.DataFrame(data=tmp.values*factors.transpose().values, index=vertexes)
                tmp_series = tmp_df.sum(axis=1)

                #E.g. tmp_series is now flattened on the option maturity
                """
                Option Mat/SwapTerm     2.0
                0.5                              
                1                       75
                3                       25
                """

                underlying_term = input_vegas.columns[j]

                v = [underlying_term]
                #convert to 5 columns
                t = pd.DataFrame(data=tmp_series, index=tmp_series.index.values, columns=v).transpose()

                #E.g. now we're attributing the values in the swap term
                """
                Option Mat/SwapTerm     1.0     3.0
                0.5                              
                1                       37.5    37.5
                3                       12.5    12.5
                """

                factors = self.__get_factors(t, ref_vertexes=vertexes)
                factors = pd.concat([factors] * 5, axis=0).transpose()
                out = pd.concat([t] * 5, axis=0)*factors.values

                #now we have a surface, so we'll add it to the other results related to this curve
                output_vegas_for_curve = output_vegas_for_curve + out

            vega_output[curve] = output_vegas_for_curve
        return vega_output

    def get_delta_output(self, json_data):
        delta_output = {}

        df = self.__get_df(json_data)

        if df is None:
            return delta_output

        df[['term']] = df[['term']].apply(pd.to_numeric)
        df = df.fillna(0)

        vertexes= [.25, .5, 1, 2, 3, 5, 10, 15, 20, 30]
        factors = self.__get_factors(df, np.array(vertexes)*365)

        table = pd.pivot_table(df, values='value', index=['term'], columns=['discriminator'], aggfunc=np.sum)
        table = table.fillna(0)
        
        for row in table:
            a_num = factors.mul(table[row], axis=0)
            delta_output[row] = a_num
        return delta_output

    def __get_factors(self, df, ref_vertexes):
        """
            By default we are going to remap 
        """
        try:
            #Should cover case for deltas
            terms = df['term'].unique().tolist()
        except:
            try:
                #Covers the case where we are remapping options
                terms = df['daysToExpiry'].unique().tolist()
            except:
                #Covers the case where we're remapping a 2d array
                terms = df.index.unique().tolist()
            ### I dislike this hack. Unfortunately the interested field varies
            ### by product. We'll need to catch up with the Veritas team 
            ### on these kinds of modelling differences.

        terms.sort()

        buckets = pd.Series(ref_vertexes)
        buckets = (buckets).astype(int)

        factors = np.zeros([len(terms), len(buckets)])
        
        #do a diagonal traversal through the array to find the factors
        #More efficient than 2 nested for loops
        i = 0

        if len(terms) == 1:
            #We'll iterate through to the first bucket that is larger or equal to ours
            for x, val in enumerate(buckets):
                if terms[0] <= val:
                    break
                else:
                    i=x

        for x, term in enumerate(terms):
            if term > buckets[i]:
                i = min(i+1, len(buckets)-1) #Making sure we don't go out of range

            if term <= buckets[i] and i == 0:
                factors[x, i] = 1
                #print("Bucket everything in first tenor")
                continue
            elif term >= buckets[i] and i == len(buckets)-1:
                factors[x, i] = 1
                #print("Bucket everything in last bucket")
                continue
            
            if term == buckets[i-1]:
                factors[x, i-1] = 1
                #print("Put exactly on one tenor")
                continue

            if term == buckets[i]:
                factors[x, i] = 1
                #print("Put exactly on one tenor")
                continue
            
            if term > buckets[i-1] and term < buckets[i]:
                lower = buckets[i-1]
                upper = buckets[i]

                upper_amount = (term - lower) / float(upper - lower)
                factors[x, i-1] = (1-upper_amount)
                factors[x, i] = upper_amount
                continue

        

        return pd.DataFrame(factors, columns=buckets, index=terms)

    def __get_df(self, json_data, type="POLICY_DELTA"):
        data = json_data['valuation']['metricValues']

        output_dict = [x for x in data if x['metric'] == type]

        if len(output_dict) == 0:
            #There isn't any data for this type
            return None

        output_dict = output_dict[0]['results']

        ###GRR AT HAVING TO ADD THIS!
        attribute = {
            "POLICY_DELTA":"buckets",
            "BUCKETED_VEGA":"vegaBuckets"
        }


        df = json_normalize(output_dict, attribute[type], ['discriminator'])
        return df