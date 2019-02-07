# external imports
import numpy as np
import gurobipy as grb

def linear_program(f, A, b, C=None, d=None, **kwargs):
    """
    Solves the linear program min_x f^T x s.t. A x <= b, C x = d.

    Arguments
    ----------
    f : numpy.ndarray
        Gradient of the cost function.
    A : numpy.ndarray
        Left-hand side of the inequality constraints.
    b : numpy.ndarray
        Right-hand side of the inequality constraints.
    C : numpy.ndarray
        Left-hand side of the equality constraints.
    d : numpy.ndarray
        Right-hand side of the equality constraints.

    Returns
    ----------
    sol : dict
        Dictionary with the solution of the LP.

        Fields
        ----------
        min : float
            Minimum of the LP (None if the problem is unfeasible or unbounded).
        argmin : numpy.ndarray
            Argument that minimizes the LP (None if the problem is unfeasible or unbounded).
        active_set : list of int
            Indices of the active inequallities {i | A_i argmin = b} (None if the problem is unfeasible or unbounded).
        multiplier_inequality : numpy.ndarray
            Lagrange multipliers for the inequality constraints (None if the problem is unfeasible or unbounded).
        multiplier_equality : numpy.ndarray
            Lagrange multipliers for the equality constraints (None if the problem is unfeasible or unbounded or without equality constraints).
    """

    # get model
    model = _build_model(f=f, A=A, b=b, C=C, d=d)

    # parameters
    model.setParam('OutputFlag', 0)
    for parameter, value in kwargs.items():
        model.setParam(parameter, value)

    # run the optimization
    model.optimize()

    # return result
    sol = _reorganize_solution(model, A, C)
    
    # get active set
    if model.status == grb.GRB.Status.OPTIMAL:
        sol['active_set'] = []
        for i in range(A.shape[0]):
            constr = model.getConstrByName('ineq_'+str(i))
            if constr.getAttr('CBasis') == -1:
                sol['active_set'].append(i)

    return sol

def quadratic_program(H, f, A, b, C=None, d=None, tol=1.e-5, **kwargs):
    """
    Solves the strictly convex (H > 0) quadratic program min .5 x' H x + f' x s.t. A x <= b, C x  = d.

    Arguments
    ----------
    H : numpy.ndarray
        Positive definite Hessian of the cost function.
    f : numpy.ndarray
        Gradient of the cost function.
    A : numpy.ndarray
        Left-hand side of the inequality constraints.
    b : numpy.ndarray
        Right-hand side of the inequality constraints.
    C : numpy.ndarray
        Left-hand side of the equality constraints.
    d : numpy.ndarray
        Right-hand side of the equality constraints.
    tol : float
        Maximum value of a multiplier to consider the related constraint inactive.

    Returns
    ----------
    sol : dict
        Dictionary with the solution of the QP.

        Fields
        ----------
        min : float
            Minimum of the QP (None if the problem is unfeasible).
        argmin : numpy.ndarray
            Argument that minimizes the QP (None if the problem is unfeasible).
        active_set : list of int
            Indices of the active inequallities {i | A_i argmin = b} (None if the problem is unfeasible).
        multiplier_inequality : numpy.ndarray
            Lagrange multipliers for the inequality constraints (None if the problem is unfeasible).
        multiplier_equality : numpy.ndarray
            Lagrange multipliers for the equality constraints (None if the problem is unfeasible or without equality constraints).
    """

    # get model
    model = _build_model(H=H, f=f, A=A, b=b, C=C, d=d)

    # parameters
    model.setParam('OutputFlag', 0)
    model.setParam('BarConvTol', 1.e-10) # with the default value (1e-8) inactive multipliers can get values such as 5e-4, setting this to 1e-10 they generally are lower than 2e-6 (note that in the following the active set is retrieved looking at the numeric values of the multipliers!)
    for parameter, value in kwargs.items():
        model.setParam(parameter, value)

    # run the optimization
    model.optimize()

    # return result
    sol = _reorganize_solution(model, A, C)

    # compute active set
    if model.status == grb.GRB.Status.OPTIMAL:
        sol['active_set'] = np.where(sol['multiplier_inequality'] > tol)[0].tolist()

    return sol

def mixed_integer_quadratic_program(nc, H, f, A, b, C=None, d=None, **kwargs):
    """
    Solves the strictly convex (H > 0) mixed-integer quadratic program min .5 x' H x + f' x s.t. A x <= b, C x  = d.
    The first nc variables in x are continuous, the remaining are binaries.

    Arguments
    ----------
    nc : int
        Number of continuous variables in the problem.
    H : numpy.ndarray
        Positive definite Hessian of the cost function.
    f : numpy.ndarray
        Gradient of the cost function.
    A : numpy.ndarray
        Left-hand side of the inequality constraints.
    b : numpy.ndarray
        Right-hand side of the inequality constraints.
    C : numpy.ndarray
        Left-hand side of the equality constraints.
    d : numpy.ndarray
        Right-hand side of the equality constraints.

    Returns
    ----------
    sol : dict
        Dictionary with the solution of the MIQP.

        Fields
        ----------
        min : float
            Minimum of the MIQP (None if the problem is unfeasible).
        argmin : numpy.ndarray
            Argument that minimizes the MIQP (None if the problem is unfeasible).
    """

    # initialize model
    model = _build_model(H=H, f=f, A=A, b=b, C=C, d=d)
    model.update()
    x = model.getVars()
    for i in range(nc, A.shape[1]):
        x[i].setAttr('vtype', grb.GRB.BINARY)
    model.update()

    # parameters
    model.setParam('OutputFlag', 0)
    for parameter, value in kwargs.items():
        model.setParam(parameter, value)

    # run the optimization
    model.optimize()

    # return result
    sol = _reorganize_solution(model, A, C, continuous=False)

    return sol

def _build_model(H=None, f=None, A=None, b=None, C=None, d=None):
    """
    Builds the Gurobi model the LP or the QP.

    Arguments
    ----------
    H, f, A, b, C, d : numpy.ndarray
        Matrices of the mathematical program.

    Returns
    ----------
    model : instance of gurobipy.Model
        Model of the mathematical program.
    """

    # initialize model
    model = grb.Model()
    n_x = max(f.shape)
    x = model.addVars(n_x, lb=[- grb.GRB.INFINITY]*n_x)

    # linear inequalities
    for i, expr in enumerate(linear_expression(A, -b, x)):
        model.addConstr(expr <= 0., name='ineq_'+str(i))

    # linear equalities
    if C is not None and d is not None:
        for i, expr in enumerate(linear_expression(C, -d, x)):
            model.addConstr(expr == 0., name='eq_'+str(i))

    # cost function
    if H is not None:
        cost = grb.QuadExpr()
        expr = quadratic_expression(H, x)
        cost.add(.5*expr)
    else:
        cost = grb.LinExpr()
    f = f.reshape(1, max(f.shape))
    expr = linear_expression(f, np.zeros((1,1)), x)
    cost.add(expr[0])
    model.setObjective(cost)

    return model

def _reorganize_solution(model, A, C, continuous=True):
    """
    Organizes the solution in a dictionary.

    Arguments
    ----------
    model : instance of gurobipy.Model
        Model of the mathematical program.
    A : numpy.ndarray
        Left-hand side of the inequality constraints.
    C : numpy.ndarray
        Left-hand side of the equality constraints.

    Returns
    ----------
    sol : dict
        Dictionary with the solution of the mathematical program.
    """

    # intialize solution
    sol = {'min': None,'argmin': None}
    if continuous:
        sol['active_set'] = None
        sol['multiplier_inequality'] = None
        sol['multiplier_equality'] = None

    # if feasible
    if model.status == grb.GRB.Status.OPTIMAL:

        # primal solution
        x = model.getVars()
        sol['min'] = model.objVal
        sol['argmin'] = np.array(model.getAttr('x')).reshape(len(x), 1)

        # dual inequalities
        if continuous:
            ineq_mult = []
            for i in range(A.shape[0]):
                constr = model.getConstrByName('ineq_' + str(i))
                ineq_mult.append(-constr.getAttr('Pi'))
            sol['multiplier_inequality'] = np.vstack(ineq_mult)

            # dual equalities
            if C is not None and C.shape[0] > 0:
                eq_mult = []
                for i in range(C.shape[0]):
                    constr = model.getConstrByName('eq_'+str(i))
                    eq_mult.append(-constr.getAttr('Pi'))
                sol['multiplier_equality'] = np.vstack(eq_mult)

    return sol

def linear_expression(A, b, x, tol=1.e-10):
    """
    Generates a list of Gurobi linear expressions A_i x + b_i (one element per row of A).

    Arguments
    ----------
    A : numpy.ndarray
        Linear term.
    b : numpy.ndarray
        Offest term.
    x : instance of gurobipy.Var
        Variable of the linear expression.
    tol : float
        Maximum absolute value for the elements of A and b to be considered nonzero.

    Returns
    ----------
    exprs : list of gurobipy.LinExpr
        List of linear expressions.
    """

    # initialize expressions
    exprs = []
    for i in range(A.shape[0]):
        expr = grb.LinExpr()

        # loop over the variables
        for j in range(A.shape[1]):

            # add linear term
            if np.abs(A[i,j]) > tol:
                expr.add(A[i,j]*x[j])

        # add offset term
        if np.abs(b[i]) > tol:
            expr.add(b[i])
        exprs.append(expr)

    return exprs

def quadratic_expression(H, x, tol=1.e-7):
    """
    Generates a Gurobi quadratic expressions x' H x.

    Arguments
    ----------
    H : numpy.ndarray
        Hessian of the quadratic expression.
    x : instance of gurobipy.Var
        Variable of the linear expression.
    tol : float
        Maximum absolute value for the elements of H to be considered nonzero.

    Returns
    ----------
    expr : gurobipy.LinExpr
        Quadratic expressions.
    """

    # initialize expression
    expr = grb.QuadExpr()
    for i in range(H.shape[0]):
        for j in range(H.shape[1]):

            # add only sufficiently big numbers
            if np.abs(H[i,j]) > tol:
                expr.add(x[i]*H[i,j]*x[j])

    return expr