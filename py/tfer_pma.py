

import sys
import scipy.optimize
import scipy.special
import numpy as np



#== TFER_1S ==============================================================#
#   Evaluates the transfer function for a PMA in Case 1S.
#   Author:   Timothy Sipkens, 2019-10-22
#
# Inputs:
#   m_star      Setpoint particle mass
#   m           Particle mass
#   d           Particle mobility diameter
#   z           Integer charge state
#   prop        Device properties (e.g. classifier length)
#   varargin    Name-value pairs for setpoint    (Optional, default Rm = 3)
#                   ('Rm',double) - Resolution
#                   ('omega1',double) - Angular speed of inner electrode
#                   ('V',double) - Setpoint voltage
#
# Outputs:
#   Lambda      Transfer function
#   G0          Function mapping final to initial radial position
#-------------------------------------------------------------------------#
def tfer_1S(sp, m, d, z, prop={}):

    tau,_,_,rs = parse_inputs(sp, m, d, z, prop)
        # parse inputs for common parameters

    #-- Estimate device parameter --------------------------------------------#
    lam = 2 * tau * (sp['alpha'] ** 2 - sp['beta'] ** 2 / (rs ** 4)) * prop['L'] / prop['v_bar']

    #-- Evaluate G0 and transfer function ------------------------------------#
    G0 = lambda r: rs + (r - rs) * np.exp(-lam) # define as a lambda function

    ra = np.minimum(prop['r2'], np.maximum(prop['r1'], G0(prop['r1'])))
    rb = np.minimum(prop['r2'], np.maximum(prop['r1'], G0(prop['r2'])))

    Lambda = (1 / (2 * prop['del'])) * (rb - ra)

    return Lambda, G0



#== TFER_1C ==============================================================#
#   Evaluates the transfer function for a PMA in Case 1C.
#   Author:   Timothy Sipkens, 2019-10-22
#
# Inputs:
#   sp          Structure defining various setpoint parameters
#               (e.g. m_star, V). Use 'get_setpoint' method to generate
#               this structure.
#   m           Particle mass
#   d           Particle mobility diameter
#   z           Integer charge state
#   prop        Device properties (e.g. classifier length)
#
# Outputs:
#   Lambda      Transfer function
#   G0          Function mapping final to initial radial position
#-------------------------------------------------------------------------#
def tfer_1C(sp, m, d, z, prop={}):

    tau,C0,_,_ = parse_inputs(sp, m, d, z, prop)
        # parse inputs for common parameters

    #-- Taylor series expansion constants ------------------------------------#
    C3 = tau * (sp['alpha'] ** 2 * prop['rc'] + 2 * sp['alpha'] * sp['beta'] / prop['rc'] + \
        sp['beta'] ** 2 / (prop['rc'] ** 3) - C0 / (m * prop['rc']))
    C4 = tau * (sp['alpha'] ** 2 - 2 * sp['alpha'] * sp['beta'] / (prop['rc'] ** 2) - \
        3 * sp['beta'] ** 2 / (prop['rc'] ** 4) + C0 / (m * (prop['rc'] ** 2)))

    #-- Evaluate G0 and transfer function ------------------------------------#
    G0 = lambda r: prop['rc'] + (r - prop['rc'] + C3 / C4) * \
        np.exp(-C4 * prop['L'] / prop['v_bar']) - C3 / C4

    ra = np.minimum(prop['r2'], np.maximum(prop['r1'], G0(prop['r1'])))
    rb = np.minimum(prop['r2'], np.maximum(prop['r1'], G0(prop['r2'])))

    Lambda = (1 / (2 * prop['del'])) * (rb - ra)

    return Lambda, G0



#== TFER_1C_DIFF =========================================================#
#   Evaluates the transfer function for a PMA in Case 1c (w/ diffusion).
#   Author:       Timothy Sipkens, 2018-12-27
#
# Inputs:
#   sp          Structure defining various setpoint parameters
#               (e.g. m_star, V). Use 'get_setpoint' method to generate
#               this structure.
#   m           Particle mass
#   d           Particle mobility diameter
#   z           Integer charge state
#   prop        Device properties (e.g. classifier length)
#
# Outputs:
#   Lambda      Transfer function
#   G0          Function mapping final to initial radial position
#-------------------------------------------------------------------------#
def tfer_1C_diff(sp, m, d, z, prop={}):

    _,_,D,_ = parse_inputs(sp, m, d, z, prop) # get diffusion coeff.
    sig = np.sqrt(2 * prop['L'] * D / prop['v_bar']) # diffusive spreading parameter

    #-- Evaluate relevant functions ------------------------------------------#
    _,G0 = tfer_1C(sp, m, d, z, prop)
        # get G0 function for this case

    rho_fun = lambda G , r: (G - r) / (np.sqrt(2) * sig) # recurring quantity
    kap_fun = lambda G , r: \
        (G - r) * scipy.special.erf(rho_fun(G, r)) + \
        sig * np.sqrt(2 / np.pi) * np.exp(-rho_fun(G,r) ** 2) # define function for kappa

    #-- Evaluate the transfer function and its terms -------------------------#
    K22 = kap_fun(G0(prop['r2']), prop['r2'])
    K21 = kap_fun(G0(prop['r2']), prop['r1'])
    K12 = kap_fun(G0(prop['r1']), prop['r2'])
    K11 = kap_fun(G0(prop['r1']), prop['r1'])
    Lambda = -1 / (4 * prop['del']) * (K22 - K12 - K21 + K11)

    # f_small = K22 > 1e2 # flag large values out of error fun. eval.
    Lambda[K22 > 1e2] = 0 # remove cases with large values out of error fun. eval.
    Lambda[np.absolute(Lambda) < 1e-10] = 0 # remove cases with roundoff error

    return Lambda, G0



#== TFER_W1 ==============================================================#
#   Evaluates the transfer function for a PMA in Case W1.
#   Author:   Timothy Sipkens, 2019-03-21
#
# Inputs:
#   sp          Structure defining various setpoint parameters
#               (e.g. m_star, V). Use 'get_setpoint' method to generate
#               this structure.
#   m           Particle mass
#   d           Particle mobility diameter
#   z           Integer charge state
#   prop        Device properties (e.g. classifier length)
#
# Outputs:
#   Lambda      Transfer function
#   G0          Function mapping final to initial radial position
#-------------------------------------------------------------------------#
def tfer_W1(sp,m,d,z,prop):

    tau,C0,_,rs = parse_inputs(sp, m, d, z, prop)
            # parse inputs for common parameters

    #-- Estimate device parameter --------------------------------------------#
    lam = 2 * tau * (sp['alpha'] ** 2 - sp['beta'] ** 2 / (rs ** 4)) * prop['L'] / prop['v_bar']


    #-- Evaluate G0 and transfer function ------------------------------------#
    G0 = lambda r: 1 / (sp['omega1'] * np.sqrt(m)) * \
        np.sqrt((m * sp['omega1'] ** 2 * r ** 2 - C0) * np.exp(-lam) + C0)

    ra = np.minimum(prop['r2'], np.maximum(prop['r1'], G0(prop['r1'])))
    rb = np.minimum(prop['r2'], np.maximum(prop['r1'], G0(prop['r2'])))

    Lambda = (1 / (2 * prop['del'])) * (rb - ra)

    return Lambda, G0



# TFER_W1_DIFF  Evaluates the transfer function for a PMA in Case E (w/ diffusion).
# Author:       Timothy Sipkens, 2018-12-27
#
# Inputs:
#   sp          Structure defining various setpoint parameters
#               (e.g. m_star, V). Use 'get_setpoint' method to generate
#               this structure.
#   m           Particle mass
#   d           Particle mobility diameter
#   z           Integer charge state
#   prop        Device properties (e.g. classifier length)
#
# Outputs:
#   Lambda      Transfer function
#   G0          Function mapping final to initial radial position
#=========================================================================#

def tfer_W1_diff(sp,m,d,z,prop):

    _,_,D,_ = parse_inputs(sp, m, d, z, prop) # get diffusion coeff.
    sig = np.sqrt(2 * prop['L'] * D / prop['v_bar']) # diffusive spreading parameter

    #-- Evaluate relevant functions ------------------------------------------#
    _,G0 = tfer_W1(sp, m, d, z, prop)
        # get G0 function for this case

    rho_fun = lambda G, r: (G - r) / (np.sqrt(2) * sig) # recurring quantity
    kap_fun = lambda G, r: \
        (G - r) * scipy.special.erf(rho_fun(G, r)) + \
        sig * np.sqrt(2 / np.pi) * np.exp(-rho_fun(G, r) ** 2) # define function for kappa

    #-- Evaluate the transfer function and its terms -------------------------#
    K22 = kap_fun(G0(prop['r2']), prop['r2'])
    K21 = kap_fun(G0(prop['r2']), prop['r1'])
    K12 = kap_fun(G0(prop['r1']), prop['r2'])
    K11 = kap_fun(G0(prop['r1']), prop['r1'])
    Lambda = -1 / (4 * prop['del']) * (K22 - K12 - K21 + K11)

    # f_small = K22 > 1e2 # flag large values out of error fun. eval.
    Lambda[K22 > 1e2] = 0 # remove cases with large values out of error fun. eval.
    Lambda[np.absolute(Lambda) < 1e-10] = 0 # remove cases with roundoff error

    return Lambda, G0



#== PARSE_INPUTS ============================================================#
# A function to evaluate setpoint parameters including C0, alpha, and beta.
# Author:  Timothy A. Sipkens, 2019-05-01
#
# Required variables:
#   sp      Mass corresponding to the measurement set point of the APM
#   d           Struct containing mutliple setpoint parameters (V, alpha, etc.)
#   m           Particle mass, can be vector of same length as d
#   z           Integer charge state, scalar
#   prop        Properties of particle mass analyzer
#
# Sample outputs:
#   C0          Summary parameter for the electrostatic force
#   tau         Product of mechanical mobility and particle mass
#   D           Diffusion coefficient for specified particles
#   rs          Equilibrium radius
#
# Notes:    As a script, this code uses variables currently in the
#           workspace. This script is also used to parse some of the inputs
#           to the various transfer functions, including the existence of
#           the integer charge state and particle mobility.
#-------------------------------------------------------------------------#
def parse_inputs(sp, m, d=0, z=1, prop={}):

    #-- Set up mobility calculations -----------------------------------------#
    e = 1.60218e-19 # electron charge [C]
    q = z * e # particle charge

    #-- Evaluate mechanical mobility -----------------------------------------#

    if d==0 or d==None: # if mobility diameter is NOT specified
        print('Invoking mass-mobility relation to determine Zp.')
        B,_,_ = mp2zp(m, z, prop['T'], prop['p'], prop)
    else: # if mobility diameter is specified
        B,_,_ = dm2zp(d, z, prop['T'], prop['p'])

    #-- Evaluate output parameters -------------------------------------------#
    tau = B * m
    D = prop['D'](B) * z # diffusion as a function of mechanical mobiltiy and charge state
    C0 = sp['V'] * q / np.log(1 / prop['r_hat']) # calcualte recurring C0 parameter

    # if required, calculate equilbirium radius
    if np.round((np.sqrt(C0 / sp['m_star']) - np.sqrt(C0 / sp['m_star'] - 4 * sp['alpha']*sp['beta'])) / (2*sp['alpha']), 15)==prop['rc']:
        rs = np.real((np.sqrt(C0 / m)- \
            np.sqrt(C0 / m - 4 * sp['alpha'] * sp['beta'])) / (2 * sp['alpha']))
    else:
        rs = np.real((np.sqrt(C0 / m) + \
            np.sqrt(C0 / m - 4 * sp['alpha'] * sp['beta'])) / (2 * sp['alpha']))

    # Calculate equilbirium radius
    # Note: Whether to pick the +ive of -ive root for rs is chosen based on a
    # heuristic approach. Specifically, the root closer to the centerline is
    # chosen, except when the -ive root is zero (which is the case for APM
    # conditions, where the +ive root should always be used).
    # to start, evaluate +ive and -ive roots
    r_m = (np.sqrt(C0/m) - \
        np.sqrt(C0/m - 4*sp['alpha']*sp['beta'])) / (2*sp['alpha'])
    r_p = (np.sqrt(C0/m) + \
        np.sqrt(C0/m - 4*sp['alpha']*sp['beta'])) / (2*sp['alpha'])

    # assign one of the two roots to rs
    rs = r_m; # by default use -ive root
    for ii in range(len(rs)): # loop through each rs
        # determine which root is closer to centerline radius
        idx = np.argmin([np.absolute(r_m[ii] - prop['rc']), \
                         np.absolute(r_p[ii] - prop['rc'])])

        # avoid zero values for APM case
        if r_m[ii]==0:
            idx = 2;

        # if closer to +ive root, use +ive root
        if idx==2:
            rs[ii] = r_p[ii];

        # zero out cases where no equilibrium radius exists (also removes complex numbers)
        if C0/m[ii] < (4*sp['alpha']*sp['beta']):
            rs[ii] = 0;


    return tau, C0, D, rs





#== GET_SETPOINT ========================================================#
#   Script to evaluate setpoint parameters including C0, alpha, and beta.
#   Author:       Timothy A. Sipkens, 2019-10-22
#
# Required variables:
#   m_star      Mass corresponding to the measurement set point of the APM
#   d           Particle mobility diameter, can be vector [nm]
#   m           Particle mass, can be vector of same length as d
#   z           Integer charge state, scalar
#   prop        Properties of particle mass analyzer
#   varargin    Name-value pairs for setpoint    (Optional, default Rm = 3)
#                   ('Rm',double) - Resolution
#                   ('omega1',double) - Angular speed of inner electrode
#                   ('V',double) - Setpoint voltage
#
# Sample outputs:
#   C0          Summary parameter for the electrostatic force
#   tau         Product of mechanical mobility and particle mass
#   sp          Struct containing mutliple setpoint parameters (V, alpha, etc.)
#
# Notes:    As a script, this code uses variables currently in the
#           workspace. This script is also used to parse some of the inputs
#           to the various transfer functions, including the existence of
#           the integer charge state and particle mobility.
#-------------------------------------------------------------------------#
def get_setpoint(prop={}, *args):

    #-- Parse inputs ---------------------------------------------------------#
    if not prop:
        prop = prop_pma()
    #-------------------------------------------------------------------------#

    #-- Initialize sp structure ----------------------------------------------#
    #   This allows for consistent order of first five entries
    sp = {'m_star': [], 'V': [], 'omega': [],
          'omega1': [], 'Rm': []} # intialize empty dictionary
    #-------------------------------------------------------------------------#

    #-- Parse inputs for setpoint --------------------------------------------#
    if len(args)==2:
        sp[args[0]] = args[1]
        sp['Rm'] = 3 # by default use resolution, with value of 3
    elif len(args)==4:
        sp[args[0]] = args[1]
        sp[args[2]] = args[3]

    #-- Set up mobility calculations -----------------------------------------#
    e = 1.60218e-19 # electron charge [C]

    #== Proceed depending on which setpoint parameters are specified =========#
    #== CASE 1: m_star is not specified, use V and omega =====================#
    if not sp['m_star']:
        # case if m_star is not specified
        # requires that voltage, 'V', and speed, 'omega' are specified

        #-- Evaluate angular speed of inner electrode ------------------------#
        if not sp['omega1']:
            sp['omega1'] = sp['omega'] / \
                ((prop['r_hat'] ** 2 - prop['omega_hat'])/(prop['r_hat'] ** 2 - 1)+ \
                prop['r1'] ** 2 * (prop['omega_hat'] - 1)/(prop['r_hat'] ** 2 - 1)/prop['rc'] ** 2)

        #-- Azimuth velocity distribution and voltage ------------------------#
        sp['alpha'] = sp['omega1'] * (prop['r_hat'] ** 2 - prop['omega_hat']) / (prop['r_hat'] ** 2 - 1)
        sp['beta'] = sp['omega1'] * prop['r1'] ** 2 * (prop['omega_hat'] - 1) / (prop['r_hat'] ** 2 - 1)

        sp['m_star']  = sp['V'] / (np.log(1/prop['r_hat']) / e * \
            (sp['alpha'] * prop['rc'] + sp['beta'] / prop['rc']) ** 2)
            # q = e, z = 1 for setpoint

        sp['omega'] = sp['alpha'] + sp['beta'] / (prop['rc'] ** 2)
        sp['omega2'] = sp['alpha'] + sp['beta'] / (prop['r2'] ** 2)


    #== CASE 2: m_star and omega1 are specified ==============================#
    elif sp['omega1']: # if angular speed of inner electrode is specified

        #-- Azimuth velocity distribution and voltage ------------------------#
        sp['alpha'] = sp['omega1'] * (prop['r_hat'] ** 2-prop['omega_hat']) / (prop['r_hat'] ** 2 - 1)
        sp['beta'] = sp['omega1'] * prop['r1'] ** 2 * (prop['omega_hat']-1) / (prop['r_hat'] ** 2 - 1)

        sp['V'] = sp['m_star'] * np.log(1 / prop['r_hat']) / e * (sp['alpha'] * prop['rc'] + sp['beta'] / prop['rc']) ** 2
            # q = e, z = 1 for setpoint

        sp['omega2'] = sp['alpha'] + sp['beta'] / (prop['r2'] ** 2)
        sp['omega'] = sp['alpha'] + sp['beta'] / (prop['rc'] ** 2)


    #== CASE 3: m_star and omega are specified ===============================#
    elif sp['omega']: # if angular speed at gap center is specified

        #-- Evaluate angular speed of inner electrode ------------------------#
        sp['omega1'] = sp['omega'] /  \
            ((prop['r_hat'] ** 2 - prop['omega_hat'])/(prop['r_hat'] ** 2 - 1) + \
            prop['r1'] ** 2 * (prop['omega_hat'] - 1) / (prop['r_hat'] ** 2 - 1) / prop['rc'] ** 2)

        #-- Azimuth velocity distribution and voltage ------------------------#
        sp['alpha'] = sp['omega1'] * (prop['r_hat'] ** 2-prop['omega_hat']) / (prop['r_hat'] ** 2-1)
        sp['beta'] = sp['omega1'] * prop['r1'] ** 2 * (prop['omega_hat'] - 1) / (prop['r_hat'] ** 2-1)

        sp['V'] = sp['m_star'] * np.log(1 / prop['r_hat']) / e * (sp['alpha'] * prop['rc'] + sp['beta'] / prop['rc']) ** 2
            # q = e, z = 1 for setpoint

        sp['omega2'] = sp['alpha'] + sp['beta'] / (prop['r2'] ** 2)


    #== CASE 4: m_star and V are specified ===================================#
    elif sp['V']: # if voltage is specified

        v_theta_rc = np.sqrt(sp['V'] * e / (sp['m_star'] * np.log(1/prop['r_hat'])))
            # q = e, z = 1 for setpoint
        A = prop['rc'] * (prop['r_hat'] ** 2-prop['omega_hat']) / (prop['r_hat'] ** 2 - 1) + \
            1 / prop['rc'] * (prop['r1'] ** 2 * (prop['omega_hat']-1) / (prop['r_hat'] ** 2 - 1))
        sp['omega1'] = v_theta_rc / A

        sp['alpha'] = sp['omega1'] * (prop['r_hat'] ** 2-prop['omega_hat']) / (prop['r_hat'] ** 2-1)
        sp['beta'] = sp['omega1'] * prop['r1'] ** 2 * (prop['omega_hat']-1) / (prop['r_hat'] ** 2-1)
        sp['omega2'] = sp['alpha']+sp['beta'] / (prop['r2'] ** 2)
        sp['omega'] = sp['alpha']+sp['beta'] / (prop['rc'] ** 2)


    #== CASE 5: m_star and Rm are specified ==================================#
    elif sp['Rm']: # if resolution is specified

        #-- Use definition of Rm to derive angular speed at centerline -------#
        #-- See Reavell et al. (2011) for resolution definition --#
        n_B = get_nb(sp['m_star'], prop)
        B_star,_,_ = mp2zp(sp['m_star'], 1, prop['T'], prop['p'], prop)

        sp['m_max'] = sp['m_star'] * (1 / sp['Rm'] + 1)
        sp['omega'] = np.sqrt(prop['Q'] / (sp['m_star'] * B_star * 2 * np.pi * prop['rc'] ** 2 * prop['L'] * \
            ((sp['m_max'] / sp['m_star']) ** (n_B + 1) - (sp['m_max'] / sp['m_star']) ** n_B)))

        #-- Evaluate angular speed of inner electrode ------------------------#
        sp['omega1'] = sp['omega'] / \
            ((prop['r_hat'] ** 2 - prop['omega_hat']) / (prop['r_hat'] ** 2 - 1) + \
            prop['r1'] ** 2 * (prop['omega_hat'] - 1) / (prop['r_hat'] ** 2 - 1) / prop['rc'] ** 2)

        #-- Azimuth velocity distribution and voltage ------------------------#
        sp['alpha'] = sp['omega1'] * (prop['r_hat'] ** 2 - prop['omega_hat']) / (prop['r_hat'] ** 2 - 1)
        sp['beta'] = sp['omega1'] * prop['r1'] ** 2 * (prop['omega_hat'] - 1) / (prop['r_hat'] ** 2 - 1)
        sp['omega2'] = sp['alpha'] + sp['beta'] / (prop['r2'] ** 2)
        sp['V'] = sp['m_star'] * np.log(1 / prop['r_hat']) / e * (sp['alpha'] * prop['rc'] + sp['beta'] / prop['rc']) ** 2


    else:
        print('No setpoint specified.')

    m_star = sp['m_star'] # output m_star independently

    if not sp['Rm']:
        sp['Rm'], sp['m_max'] = get_resolution(sp['m_star'], sp['omega'], prop)
            # evaluate resolution in corresponding subfunction
            # involves a minimization routine

    return sp, m_star



#== GET_RESOLUTION =======================================================#
#   Solver to evaluate the resolution from m_star and prop.
def get_resolution(m_star, omega, prop):

    print('Finding resolution...')

    n_B = get_nb(m_star, prop)

    B_star,_,_ = mp2zp(m_star, 1, \
        prop['T'], prop['p'], prop) # mechanical mobility for z = 1

    t0 = prop['Q'] / (m_star * B_star * 2 * np.pi * prop['L'] * \
        omega ** 2 * prop['rc'] ** 2) # RHS of Eq. (10) in Reveall et al.

    m_rat = lambda Rm: 1 / Rm + 1 # function for mass ratio
    fun = lambda Rm: (m_rat(Rm)) ** (n_B + 1) - (m_rat(Rm)) ** n_B # LHS of Eq. (10) in Reveall et al.

    Rm = scipy.optimize.fmin(lambda Rm: (t0 - fun(Rm))**2, x0=5) # minimization ot find Rm
    Rm = Rm[0] # convert ndarray to float
    m_max = m_star * (1 / Rm + 1) # approx. upper end of non-diffusing tfer. function

    print('Complete.')
    print(' ')

    return Rm, m_max



#== GET_NB ===============================================================#
#   Function to evaluate n_B constant. Taken from Olfert laboratory.
#   Note: Previous versions of this program would output a constant
#   value of n_B = -0.6436. This will cause some rather  minor
#   compatiblity issues.
#-------------------------------------------------------------------------#
def get_nb(m_star, prop):

    m_high = m_star * 1.001 # perturb m_star up
    m_low  = m_star * .999 # perturb m_star down

    B_high,_,_ = mp2zp(m_high, 1, prop['T'], prop['p'], prop)
    B_low,_,_ = mp2zp(m_low, 1, prop['T'], prop['p'], prop)

    n_B = np.log10(B_high / B_low) / np.log10(m_high / m_low) # constant from Reveall et al.

    # n_B = -0.6436 # deprecated value

    return n_B



#== DM2ZP ================================================================#
#   Function to calculate electric mobility from a vector of mobility diameter.
#   Author:  Timothy Sipkens, 2019-10-22
#
# Inputs:
#   d           Particle mobility diameter
#   z           Integer charge state
#   T           System temperature  (Optional)
#   P           System pressure     (Optional)
#
# Outputs:
#   Zp          Electromobility
#   B           Mechanical mobility
#
# Notes:
# 2 Some of the code is adapted from Buckley et al. (2017) and Olfert
#   laboratory.
#-------------------------------------------------------------------------#
def dm2zp(d, z, T=0.0, p=0.0):

    e = 1.6022e-19 # define electron charge [C]

    if T==0.0 or p==0.0:
        mu = 1.82e-5 # gas viscosity [Pa*s]
        B = Cc(d) / (3 * np.pi * mu * d) # mechanical mobility
    else:
        S = 110.4 # temperature [K]
        T_0 = 296.15 # reference temperature [K]
        vis_23 = 1.83245e-5 # reference viscosity [kg/(m*s)]
        mu = vis_23 * ((T / T_0) ** 1.5) * ((T_0 + S)/(T + S)) # gas viscosity
            # Kim et al. (2005), ISO 15900, Eqn 3
        B = Cc(d,T,p) / (3 * np.pi * mu * d) # mechanical mobility

    Zp = B * e * z # electromobility

    return B, Zp



#== CC ===================================================================#
#   Function to evaluate Cunningham slip correction factor.
#   Author:  Timothy Sipkens, 2019-10-22
#
# Inputs:
#   d           Particle mobility diameter
#   T           System temperature  (Optional)
#   P           System pressure     (Optional)
#
# Outputs:
#   Zp          Electromobility
#   B           Mechanical mobility
#-------------------------------------------------------------------------#
def Cc(d, T=0.0, p=0.0):

    if T==0.0 or p==0.0: # if P and T are not specified, use Buckley/Davies
        mfp = 66.5e-9 # mean free path

        # for air, from Davies (1945)
        A1 = 1.257
        A2 = 0.4
        A3 = 0.55

    else: # from Olfert laboratory / Kim et al.
        S = 110.4 # temperature [K]
        mfp_0 = 6.730e-8 # mean free path of gas molecules in air [m]
        T_0 = 296.15 # reference temperature [K]
        p_0 = 101325 # reference pressure, [Pa] (760 mmHg to Pa)

        p = p * p_0

        mfp = mfp_0 * (T / T_0) ** 2 * (p_0 / p) * ((T_0 + S) / (T + S)) # mean free path
            # Kim et al. (2005) (doi:10.6028/jres.110.005), ISO 15900 Eqn 4

        A1 = 1.165
        A2 = 0.483
        A3 = 0.997 / 2


    Kn = (2 * mfp) / d # Knudsen number
    Cc = 1 + Kn * (A1 + A2 * np.exp(-(2 * A3) / Kn)) # Cunningham slip correction factor

    return Cc



#== MP2ZP ================================================================#
#   Calculate electric mobility from a vector of particle mass.
#   Author:   Timothy Sipkens, 2019-10-22
#
# Inputs:
#   m           Particle mass
#   z           Integer charge state
#   T           System temperature
#   P           System pressure
#
# Outputs:
#   Zp          Electromobility
#   B           Mechanical mobility
#   d           Mobility diameter (simplied by mass-mobility relation)
#
# Note:
#   Uses mass-mobility relationship to first convert to a mobility
#   diameter and then estimates the mobility using dm2zp.
#-------------------------------------------------------------------------#
def mp2zp(m, z, T=0.0, P=0.0, prop={}):

    #-- Parse inputs ---------------------------------------------------------#
    if not bool(prop) or hasattr(prop, 'm0') or hasattr(prop, 'Dm'):
         sys.exit('Please specify the mass-mobility relation parameters in prop.')
             # if isempty or missing elements, produce error
    #-------------------------------------------------------------------------#

    d = 1e-9 * (m / prop['m0']) ** (1 / prop['Dm'])
        # use mass-mobility relationship to get mobility diameter

    #-- Use mobility diameter to get particle electro and mechanical mobl. ---#
    if T==0.0 or P==0.0:
        B, Zp = dm2zp(d,z)
    else:
        B, Zp = dm2zp(d,z,T,P)

    return B, Zp, d



#== PROP_PMA =============================================================#
#   Generates the prop struct used to summarize CPMA parameters.
#   Author:   Timothy Sipkens, 2019-10-22
#
# Input:
#   opt         Options string specifying parameter set
#                   (Optional, default 'Olfert')
#
# Output:
#   prop        Properties struct for use in evaluating transfer function
#-------------------------------------------------------------------------#
def prop_pma(opts='Olfert'):

    #-- CPMA parameters from Olfert lab ----------------------------------#
    if opts=='Olfert':
        prop = {
            'r1': 0.06, # inner electrode radius [m]
            'r2': 0.061, # outer electrode radius [m]
            'L': 0.2, # length of chamber [m]
            'p': 1, # pressure [atm]
            'T': 293, # system temperature [K]
            'Q': 3/1000/60, # volume flow rate (m ** 3/s) (prev: ~1 lpm)
            'omega_hat': 32/33 # ratio of angular speeds
        }

    #-- CPMA/APM parameters from Buckley et al. --------------------------#
    elif opts=='Buckley':
        prop = {
            'r1': 0.025, # inner electrode radius [m]
            'r2': 0.024, # outer electrode radius [m]
            'L': 0.1, # length of chamber [m]
            'omega': 13350*2*np.pi/60, # rotational speed [rad/s]
            'p': 1, # pressure [atm]
            'T': 298, # system temperature [K]
            'Q': 1.02e-3/60, # volume flow rate (m ** 3/s) (prev: ~1 lpm)
            'omega_hat': 1 # ratio of angular speeds
        }

    #-- Parameters related to CPMA geometry ----------------------------------#
    prop['rc'] = (prop['r1']+prop['r2'])/2
    prop['r_hat'] = prop['r1']/prop['r2']
    prop['del'] = (prop['r2']-prop['r1'])/2 # half gap width

    prop['A'] = np.pi*(prop['r2']**2-prop['r1']**2) # cross sectional area of APM
    prop['v_bar'] = prop['Q']/prop['A'] # average flow velocity


    #-- For diffusion --------------------------------------------------------#
    kB = 1.3806488e-23 # Boltzmann's constant
    prop['D'] = lambda B: kB * prop['T'] * B # diffusion coefficient


    #-- Default mass-mobility information -------------#
    prop['Dm'] = 3 # mass-mobility exponent
    prop['m0'] = 4.7124e-25 # mass-mobility relation density
    # Common alternate: Dm = 2.48 m0 = 2.9280e-24


    return prop
