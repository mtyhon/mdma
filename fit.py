import torch as t
import torch.optim as optim
import models
import copy


def fit_neural_copula(data,
                      h,
                      verbose=True,
                      print_every=20,
                      checkpoint_every=100):
  # h: dictionary of hyperparameters
  # default hyperparameters
  default_h = {
      'n': 200,
      'M_val': 500,
      'n_iters': 600,
      'update_z_every': 1,
      'b_std': 0.01,
      '_std': 0.01,
      'a_std': 0.01,
      'lambda_l2': 1e-4,
      'lambda_hess_full': 0,
      'lambda_hess_diag': 0,
      'lambda_ent': 0,
      'clip_max_norm': 0,
      'decrease_lr_time': 1,
      'decrease_lr_factor': 0.1,
      'bp_through_z_update': False,
      'opt': 'adam',
      'lr': 5e-3,
  }

  # merge h and default_h, overriding values in default_h with those in h
  h = {**default_h, **h}

  model = models.CopNet(h['n'],
                        h['d'],
                        b_bias=0,
                        b_std=h['b_std'],
                        _std=h['_std'],
                        a_std=h['a_std'],
                        z_update_samples=h['M'])
  train_data, val_data = data

  with t.no_grad():
    if h['lambda_hess_diag'] > 0:
      tr_hess_sq_0 = t.mean(model.diag_hess(train_data)**2)
    if h['lambda_hess_full'] > 0:
      hess_norm_sq_0 = model.hess(train_data).norm()**2

  if h['opt'] == 'adam':
    optimizer = optim.Adam(model.parameters(), lr=h['lr'])
  elif h['opt'] == 'sgd':
    optimizer = optim.SGD(model.parameters(), lr=h['lr'])
  else:
    raise NameError

  scheduler = t.optim.lr_scheduler.StepLR(optimizer,
                                          step_size=int(h['decrease_lr_time'] *
                                                        h['n_iters']),
                                          gamma=h['decrease_lr_factor'])

  t.autograd.set_detect_anomaly(True)

  # fit neural copula to data
  nlls = []
  val_nlls = []
  checkpoints = []
  checkpoint_iters = []
  best_val_nll = t.tensor(float("Inf"))
  print(h)
  for i in range(h['n_iters']):
    # update parameters
    optimizer.zero_grad()
    nll = model.nll(train_data)
    val_nll = model.nll(val_data)
    obj = nll

    # regularization
    L2 = (t.norm(model.w)**2 + t.norm(model.a)**2 + t.norm(model.b)**2)
    obj += h['lambda_l2'] * L2

    if h['lambda_ent'] > 0:
      samples = model.sample(h['M'], n_bisect_iter=25)
      ent = model.nll(samples)
      obj = obj - h['lambda_ent'] * ent

    if h['lambda_hess_diag'] > 0:
      tr_hess_sq = t.mean(model.diag_hess(train_data)**2) / tr_hess_sq_0
      obj += h['lambda_hess_diag'] * tr_hess_sq

    if h['lambda_hess_full'] > 0:
      hess_norm_sq = model.hess(train_data).norm()**2 / hess_norm_sq_0
      obj += h['lambda_hess_full'] * hess_norm_sq

    obj.backward()

    if h['clip_max_norm'] > 0:
      t.nn.utils.clip_grad_value_(model.parameters(), h['clip_max_norm'])

    optimizer.step()
    scheduler.step()

    # update z approximation, can also take the data as input
    if i % h['update_z_every'] == 0:
      model.update_zs(bp_through_z_update=h['bp_through_z_update'])

    nlls.append(nll.cpu().detach().numpy())
    val_nlls.append(val_nll.cpu().detach().numpy())
    if val_nll < best_val_nll:
      best_val_nll = val_nll.detach().clone()
      best_val_nll_model = copy.deepcopy(model)

    if verbose and i % print_every == 0:
      print('iteration {}, train nll: {:.4f}, val nll: {:.4f}'.format(
          i,
          nll.cpu().detach().numpy(),
          val_nll.cpu().detach().numpy(),
      ))

    if (i + 1) % checkpoint_every == 0:
      checkpoints.append(copy.deepcopy(model))
      checkpoint_iters.append(i)

    if i > 300 and nll > 0:
      print('fitting unstable, terminating')
      break

  outs = {
      'nlls': nlls,
      'val_nlls': val_nlls,
      'model': model,
      'h': h,
      'data': data,
      'checkpoints': checkpoints,
      'checkpoint_iters': checkpoint_iters,
      'best_val_nll_model': best_val_nll_model
  }

  return outs
