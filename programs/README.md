# DAS Programs 

The primary codebase for DAS, as invoked by `das_framework/driver.py`.

Scripts included provide for operations related to experiment construction, dataset reading/writing, constraint definition, solver bindings, metric calculation, and validation.

Main directory contains:
+ The setup module for DAS development on Research 2 and on EMR clusters.
+ Validator for for calculating sum of absolute values of histogram differences.
+ Utilities for zipping the files in das_decennial folder and indicated subfolders to have as submodules when shipping to Spark

What follows is a brief summary of the major components of each subdirectory


# Engine

+ Topdown engine
    - Creates the Geo Nodes without DP data and aggregates.
    - Creates noisy measurements
    - Topdown algorithm implementation


+ Gurobi interface
    - Manage environments for the C Gurobi wrapper


+ Solver setup for the geography imputation problem using the L2 solution from Gurobi.
    - Variable number of geographies we impute to
    - Sets up noise weights for solve given a variety of queries
    - Provdes Constraint specification


+ Invariants maintenance and checkup
    

+ Helper methods
    - Node IP acquisition


+ Primitive operations used in differential privacy.
    - Implementation of the Geometric Mechanism for differential privacy
        Adding noise from the (two-sided) Geometric distribution, with p.d.f (of integer random variable k):

                      p          -│k│       1 - α    -│k│
                   ──────── (1 - p)     or  ──────── α
                    2 - p                   1 + α

        where p is the parameter, or α = 1 - p in different conventional notation

    - Implements Laplace mechanism for differential privacy.
        Adding noise from the Laplace distribution, with p.d.f

                          1      -│x-a│
                        ───── exp ───────,
                         2b         b

        where a is known as the location, and b as the scale of Laplace distribution


# Experiment

+ Experiment Interface
    - Provides class interface for creating a series of experiments with different privacy budgets and other configuration options
    - Works on collections of configurable budget groups


# Metrics

+ Error Metrics
    - Metric Groups contain results of metrics as sun on Geo Units (metric values, runtime, etc.)
    - L1, L2, L-Inf error metrics included


+ Resma (Results Multiarray) 
    - Generated by the (geolevels, aggtypes, metrics) tuples/dictionary created by the DAS Error Metrics class and stored within the Metric Group object.
    - Resmas are structured as 3-dimensional arrays and follow a pattern similar to the error metric results keys: `(geolevels, aggtypes, metrics)`. 
    - Resmas make it easier to analyze and visualize the error metric results.


# Reader

+ MDF Input
    - Reads MDF format data for DAS processing
    - Supports conversion between inconsistent dataset formats into the supported standard

+ Contraints/Invariants
    - Creates constraint objects from what is listed in the config file
    - Stores invariants as specified for later validation

+ Recoder
    - Variable recoder library for the different test data sets.
    - The recode method operates on a single SparkDataFrame row


# Writer

+ MDF Output
    - Writes MDF format results out to configured destination
    - Parts can be concatenated together from distributed pieces to create final result