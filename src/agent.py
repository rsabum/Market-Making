import numpy as np
from tqdm import tqdm
from .simulation import MarketState

class KalmanFilter(object):
    pass

class ValueFunction(object):
    def __init__(self, t_grid, q_grid, V, PI):
        """
        Initializes the SolverOutput class with the specified parameters.

        Parameters:
        -----------
        q_grid : list
            A list representing the q grid.
        t_grid : list
            A list representing the t grid.
        h : np.ndarray
            A numpy array representing the optimal 
            value function at each q and t value.
        """

        self.q_grid = q_grid
        self.t_grid = t_grid

        self.t_lookup = {t: i for i, t in enumerate(t_grid)}
        self.q_lookup = {q: i for i, q in enumerate(q_grid)}

        self.V = V
        self.PI = PI
    
    def get_value(self, t, q):
        """
        Returns the policy at the specified time and inventory level.

        Parameters:
        -----------
        t : float
            The time at which to evaluate the policy.
        q : float
            The inventory level at which to evaluate the policy.

        Returns:
        --------
        tuple
            The policy at the specified time and inventory level.
        """

        # Find the closest time step to the specified time
        t_idx = self.t_lookup[t]
        q_idx = self.q_lookup[q]

        return self.V[t_idx, q_idx]
    
    def get_policy(self, t, q):
        """
        Returns the policy at the specified time and inventory level.

        Parameters:
        -----------
        t : float
            The time at which to evaluate the policy.
        q : float
            The inventory level at which to evaluate the policy.

        Returns:
        --------
        tuple
            The policy at the specified time and inventory level.
        """

        # Find the closest time step to the specified time
        t_idx = self.t_lookup[t]
        q_idx = self.q_lookup[q]

        return self.PI[(t_idx, q_idx)]


class MarketMaker(object):

    def solve_hjb_qvi(
        self, 
        lambda_bid, 
        lambda_ask, 
        kappa_bid, 
        kappa_ask, 
        rebate,
        cost,
        phi, 
        alpha, 
        T, 
        N, 
        q_min, 
        q_max
    ):
        """
        Solves the optimal order size for a long only 
        trading algorithm using backward Euler finite 
        difference scheme.

        Parameters:
        -----------
        lambda_bid : float
            The bid side order flow intensity.
        lambda_ask : float
            The ask side order flow intensity.
        kappa_bid : float
            The bid side order flow decay.
        kappa_ask : float
            The ask side order flow decay.
        cost : float
            The cost of sending a market order.
        rebate : float
            The rebate for providing liquidity.
        phi : float
            The running inventory penalty parameter.
        alpha : float
            The terminal inventory penalty parameter.
        T : float
            The terminal time.
        N : int
            The number of time steps.
        q_min : int
            The minimum inventory level.
        q_max : int
            The maximum inventory level.

        Returns:
        --------
        None
        """         

        # time grid and time step size
        dt = T / N
        t_grid = np.linspace(0, T, N + 1)

        # Inventory grid
        q_grid = np.arange(q_min, q_max + 1)  # Inventory grid

        # Initialize the value function V and policy function PI
        V = np.zeros((len(t_grid), len(q_grid)))
        PI = {}

        # Set the terminal condition: V(T, q) = -alpha * q^2
        V[-1, :] = -alpha * q_grid ** 2

        print("Solving HJB-QVI...")
        max_error = 1e-9
        for i in tqdm(range(N, 0, -1)):  # Iterate backward over time steps
            error = 1e9

            # solve the quasi-variational inequality using value iteration 
            while error > max_error:
                V_prime = np.zeros(len(q_grid))

                for j, q_j in enumerate(q_grid):
                    B = max(0, 1/kappa_bid - rebate - (V[i, j + 1] - V[i, j])) if q_j < q_max else None
                    A = max(0, 1/kappa_ask - rebate - (V[i, j - 1] - V[i, j])) if q_j > q_min else None
                    V_mb = V[i - 1, j + 1] - cost if q_j < q_max else -np.inf
                    V_ms = V[i - 1, j - 1] - cost if q_j > q_min else -np.inf
                    V_mm = V[i, j] + dt * (
                        (lambda_bid * np.exp(-kappa_bid * B) * 
                        (B + rebate + V[i, j + 1] - V[i, j]) if B else 0) + 
                        (lambda_ask * np.exp(-kappa_ask * A) * 
                        (A + rebate + V[i, j - 1] - V[i, j]) if A else 0) - 
                        phi * q_j ** 2
                    )

                    k = np.argmax([V_mb, V_ms, V_mm])
                    
                    if k == 0:
                        V_prime[j] = V_mb
                        PI[(i - 1, j)] = ("market_buy", None, None)
                    elif k == 1:
                        V_prime[j] = V_ms
                        PI[(i - 1, j)] = ("market_sell", None, None)
                    else:
                        V_prime[j] = V_mm
                        PI[(i - 1, j)] = ("market_make", B, A)


                error = np.linalg.norm(V_prime - V[i - 1])
                V[i - 1] = V_prime
                    

        self.V = ValueFunction(t_grid, q_grid, V, PI)
                    
    
    def run(self, state: MarketState) -> dict[str, any]:
        pass